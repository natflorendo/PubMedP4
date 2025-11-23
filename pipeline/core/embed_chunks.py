"""
embed_chunks.py

Generate embeddings for text chunks stored in PostgreSQL, using a
SentenceTransformer model, and persist the results in chunk_embeddings.

Usage:
python3 -m core.embed_chunks --log-level INFO
"""

from __future__ import annotations

import argparse
import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

import psycopg
from psycopg.rows import dict_row
from sentence_transformers import SentenceTransformer

from pipeline.config.config import PipelineConfig, load_config

# frozen=True means it automatically generates an immutable class with an __init__ method.
# (once created, you can’t change its fields)
@dataclass(frozen=True)
class ChunkRow:
    chunk_id: int  # Primary key for chunk
    pmid: int      # Reference to the PubMed article
    text: str      # Chunk text extracted from article

def _compute_hash(text: str) -> str:
    """Compute a short SHA256 hash for a chunk’s text (used for staleness detection)."""
    # Get first 16 characters
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

def fetch_todo_chunks(conn: psycopg.Connection, model_name: str) -> List[ChunkRow]:
    """
    Return only the chunks that do not yet have embeddings for the given model
    or have an embedding whose text hash no longer matches.
    """
    # `with` means that the file will automatically close once the block ends and 
    # if an error happens during parsing, Python will cleanly close the file.
    # A database cursor is a temporary object for executing SQL commands and fetching results.
    # row_factory=dict_row means each row returned from the query will be a dictionary instead of a tuple.
    with conn.cursor(row_factory=dict_row) as cur:
        # Fetch chunks that are either missing embeddings or have outdated ones.
        # LEFT JOIN matches all chunks in text_chunks to existing embeddings for the same model.
        # `ce.chunk_id IS NULL` = chunk has never been embedded for this model.
        # `ce.text_hash <> ...` = chunk text changed since the last embedding (stale).
        cur.execute(
            """
            SELECT tc.chunk_id, tc.pmid, tc.chunk_text
            FROM text_chunks AS tc
            LEFT JOIN chunk_embeddings AS ce
              ON tc.chunk_id = ce.chunk_id AND ce.model_name = %s
            WHERE ce.chunk_id IS NULL
               OR ce.text_hash <> substring(tc.content_hash FOR 16)
            ORDER BY tc.pmid, tc.chunk_id
            """,
            (model_name,),
        )

        # Fetch all rows returned by the query and wrap each as a ChunkRow dataclass.    
        todo_rows = [
            ChunkRow(chunk_id=row["chunk_id"], pmid=row["pmid"], text=row["chunk_text"])
            for row in cur.fetchall()
        ]
    return todo_rows


def delete_embeddings(conn: psycopg.Connection, current_model: str) -> int:
    """Delete embeddings if the stored model differs from current_model."""
    with conn.cursor(row_factory=dict_row) as cur:
        # Fetch unique model_name values that already exist
        cur.execute("SELECT DISTINCT model_name FROM chunk_embeddings")
        # Create a list of the version strings
        existing_models = [row["model_name"] for row in cur.fetchall()]
        # Clean up all models stored that do not match the current one
        if existing_models and any(v != current_model for v in existing_models):
            logging.info(
                "Found outdated models in database: %s. Keeping only %s.",
                ", ".join(existing_models),
                current_model,
            )
            # Deletes all rows where model_ is not equal to the current version.
            cur.execute(
                "DELETE FROM chunk_embeddings WHERE model_name <> %s",
                (current_model,),
            )
            # Returns how many embeddings were deleted.
            return cur.rowcount
    # No outdated versions found, or empty table.
    return 0


def insert_embeddings(
    conn: psycopg.Connection,
    rows: Iterable[ChunkRow],
    embeddings,
    model_name: str,
) -> None:
    """Store embeddings to the database."""
    with conn.cursor() as cur:
        # `executemany()` runs the same SQL command repeatedly for many rows
        # For ON CONFLICT, if a row already exists for a chunk_id & model_name update it with new data.
        cur.executemany(
            """
            INSERT INTO chunk_embeddings (chunk_id, pmid, model_name, embedding_dim, embedding, text_hash)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (chunk_id, model_name) DO UPDATE
            SET embedding = EXCLUDED.embedding,
                embedding_dim = EXCLUDED.embedding_dim,
                text_hash = EXCLUDED.text_hash,
                created_at = CURRENT_TIMESTAMP
            """,
            [
                (
                    row.chunk_id,
                    row.pmid,
                    model_name,
                    len(emb),
                    [float(x) for x in emb],
                    _compute_hash(row.text),
                )
                # `strict=True` ensures both lists are the same length.
                for row, emb in zip(rows, embeddings, strict=True)
            ],
        )


def run(config: PipelineConfig) -> None:
    # Extract embed configuration section.
    embed_cfg = config.embed
    logging.info("Loading model %s", embed_cfg.model)
    # Downloads (if not cached) and initializes the model to generate text embeddings.
    model = SentenceTransformer(embed_cfg.model)

    # Connect to the database using the connection string from config
    with psycopg.connect(config.database.url) as conn:
        # Ensures all SQL commands target the public schema.
        conn.execute("SET search_path TO public")

        # Remove embeddings if it uses an outdated model
        deleted = delete_embeddings(conn, embed_cfg.model)
        if deleted:
            logging.info("Removed %d existing embeddings for %s", deleted, embed_cfg.model)

        # Fetches only text chunks that need to be embedded.
        rows_to_embed = fetch_todo_chunks(conn, embed_cfg.model)
        if not rows_to_embed:
            logging.warning("No new or unembedded chunks found. (Run parse_directory.py first if no chunks exist)")
            return

        logging.info("Encoding %d chunks (batch_size=%d)", len(rows_to_embed), embed_cfg.batch_size)
        # Do embeddings
        embeddings = model.encode(
            # Get text from each ChunkRow.
            [row.text for row in rows_to_embed],
            # How many chunks are processed in one forward pass.
            batch_size=embed_cfg.batch_size,
            show_progress_bar=True,
            convert_to_numpy=True,
            normalize_embeddings=embed_cfg.normalize,
        )
        
        # Write embeddings into chunk_embeddings table
        insert_embeddings(conn, rows_to_embed, embeddings, embed_cfg.model)
        # Count all embeddings in the database for the current model and retrieve the count value.
        total = conn.execute(
            "SELECT COUNT(*) FROM chunk_embeddings WHERE model_name = %s",
            (embed_cfg.model,),
        ).fetchone()[0]
        logging.info("Stored %d embeddings for model %s", total, embed_cfg.model)

        # Gets the total number of chunks and checks if it matches with the model total.
        chunks_total = conn.execute("SELECT COUNT(*) FROM text_chunks").fetchone()[0]
        if total != chunks_total:
            logging.warning(
                "Embedding count (%d) does not match chunk count (%d)",
                total,
                chunks_total,
            )
        else:
            logging.info("Embedding count matches chunk count (%d)", total)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the embedding pipeline. Allows customization of runtime behavior"""
    # The `description` and `help` text will appear if someone runs: python3 -m core.embed_chunks --help
    parser = argparse.ArgumentParser(description="Embed text chunks with SentenceTransformers.")
    # Path(__file__) creates a Path object pointing to the current Python file.
    # .resolve() converts that into an absolute path, resolving any .. or symbolic links.
    # .parents[1] goes one directory up from the file’s location.
    # /"config"/"config.toml" appends the subdirectory and filename
    # Then convert the Path to a string because argparse expects a plain string.
    parser.add_argument(
        "--config",
        default=str(Path(__file__).resolve().parents[1] / "config" / "config.toml"),
        help="Path to config.toml (default: %(default)s)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity (default: %(default)s)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level))
    config = load_config(args.config)
    run(config)


if __name__ == "__main__":
    main()
