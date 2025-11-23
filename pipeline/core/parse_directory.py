"""
parse_directory.py

Parses and chunks all PubMed documents in a given directory and stores results in PostgreSQL.

Usage:
python3 -m core.parse_directory --log-level INFO
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Iterable

import psycopg

from pipeline.config.config import InputConfig, PipelineConfig, load_config
from pipeline.core.chunker import chunk_text, normalize_text
from pipeline.core.pdf_reader import read_document
from pipeline.utils.metadata_loader import MetadataStore, upload_metadata_to_db, load_metadata_rows
from pipeline.utils.db_writer import ensure_pubmed_document_entry, upsert_chunks


def process_document(
    conn: psycopg.Connection,
    path: Path,
    metadata_store: MetadataStore,
    input_config: InputConfig,
) -> int:
    """Process one document end-to-end and store its chunks into the database."""
    raw_text = read_document(path)
    # Remove extra whitespace and drop non-ASCII characters
    normalized = normalize_text(raw_text)
    # Match article with its metadata entry in the database
    article = metadata_store.resolve(path, normalized)
    # Inserts or updates a row in the documents table to represent this file.
    ensure_pubmed_document_entry(conn, article)
    # Divide the text into overlapping chunks for embedding
    chunks = chunk_text(
        article.pmid,
        normalized,
        chunk_size=input_config.chunk_size,
        overlap_ratio=input_config.overlap_ratio,
    )
    if not chunks:
        logging.warning("No chunks generated for %s; document remains unprocessed.", path.name)
        return 0
    # Insert/update new chunks and delete any stale ones, then mark the document as processed.
    upsert_chunks(conn, chunks)
    logging.info("Processed %s -> %d chunks", path.name, len(chunks))
    return len(chunks)


def gather_files(raw_dir: Path) -> Iterable[Path]:
    """Scans a directory for files matching PDF and text file patterns."""
    # Iterates twice: once for `*.pdf` and once for `*.txt`
    for pattern in ("*.pdf", "*.txt"):
        # Instead to returning a list, yield results one by one (more memory efficient)
        # .glob() is a pathlib method that searches the directory for all files that match the pattern.
        # sorted to create deterministic order.
        yield from sorted(raw_dir.glob(pattern))


def run(config: PipelineConfig) -> None:
    # Get input section of config
    input_config = config.input
    raw_dir = input_config.raw_dir
    if not raw_dir.exists():
        raise FileNotFoundError(f"Raw directory {raw_dir} does not exist")

    # Open the CSV, parse each row, and convert them into a list of ArticleMetadata objects.
    metadata_rows = load_metadata_rows(input_config.metadata_csv)
    # Wrap the list of metadata objects in a MetadataStore class for fast lookup.
    # Enables quick matching between documents and metadata (looking for DOI or title in normalized article text)
    metadata_store = MetadataStore(metadata_rows)

    # `with` means that the file will automatically close once the block ends and 
    # if an error happens during parsing, Python will cleanly close the file.
    # Open a PostgreSQL connection using the configured database URL
    with psycopg.connect(config.database.url) as conn:
        # Explicitly set the schema to public
        conn.execute("SET search_path TO public")
        # Insert or update entries in `pubmed_articles`, `journals`, `authors`, and `pubmed_authors`.
        upload_metadata_to_db(conn, metadata_rows)
        attempted_docs = 0  # how many files were found and attempted
        processed_docs = 0  # how many successfully produced chunks
        total_chunks = 0    # total number of chunks created and inserted

        # Yields one path at a time to stream through the directory without loading everything into memory.
        for path in gather_files(raw_dir):
            attempted_docs += 1
            # Ensures that all changes for this file are atomic.
            # If something fails halfway through, the transaction rolls back automatically.
            with conn.transaction():
                try:
                    chunk_count = process_document(conn, path, metadata_store, input_config)
                except Exception as exc:
                    logging.exception("Failed to process %s: %s", path.name, exc)
                    continue
                # Only update progress metrics if chunks were successfully created.
                if chunk_count:
                    processed_docs += 1
                    total_chunks += chunk_count

        # Give how many documents processed and the total number of chunks created.
        logging.info(
            "Processed %d/%d documents into %d chunks",
            processed_docs,
            attempted_docs,
            total_chunks,
        )
        count = conn.execute("SELECT COUNT(*) FROM text_chunks").fetchone()[0]
        # Gives the total number of chunk rows in the database (useful for debugging).
        logging.info("Database now holds %d total chunks", count)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the parsing and chunking pipeline. Allows customization of runtime behavior"""
    # The `description` and `help` text will appear if someone runs: python3 -m core.parse_directory --help
    parser = argparse.ArgumentParser(description="Run the ingestion pipeline.")
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
        help="Logging level (default: %(default)s)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level))
    config = load_config(args.config)
    run(config)


if __name__ == "__main__":
    main()
