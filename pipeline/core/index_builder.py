"""
index_builder.py

Builds and maintains a FAISS index over chunk embeddings.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Tuple

import faiss
import numpy as np
import psycopg

from config.config import PipelineConfig

from dotenv import load_dotenv
load_dotenv()

ARTIFACTS_DIR = Path(__file__).resolve().parents[1] / "artifacts"
DEFAULT_INDEX_PATH = ARTIFACTS_DIR / "index_flat.faiss"


def _ensure_artifact_dir(path: Path) -> None:
    """Guarantees that the directory for the output file exists before writing."""
    # parents=True ensures that all the parent directoies exist
    # exist_ok=True continues silently if the dirctory already exists instead of raising an error.
    path.parent.mkdir(parents=True, exist_ok=True)


def _fetch_embeddings(conn: psycopg.Connection, model_name: str) -> Tuple[np.ndarray, np.ndarray]:
    """Retrieve all stored embeddings for a given model from the database."""
    # `with` means that the file will automatically close once the block ends and 
    # if an error happens during parsing, Python will cleanly close the file.
    # A database cursor is a temporary object for executing SQL commands and fetching results.
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT chunk_id, embedding
            FROM chunk_embeddings
            WHERE model_name = %s
            ORDER BY chunk_id
            """,
            (model_name,),
        )
        rows = cur.fetchall()
    if not rows:
        raise RuntimeError(
            "No embeddings found for model %s. Run embed_chunks.py first." % model_name
        )
    # Extracts the chunk IDs and converts them into a NumPy array of type int64.    
    chunk_ids = np.array([row[0] for row in rows], dtype="int64")
    # Extracts the embedding vectors and converts each to a NumPy array of 32-bit floats, 
    # then stacks them vertically into a 2D array.
    # FAISS requires all embeddings to have the same length
    embeddings = np.stack([np.array(row[1], dtype="float32") for row in rows])
    return chunk_ids, embeddings


def build_index(
    config: PipelineConfig,
    model_name: str | None = None,
    index_path: Path | None = None,
) -> Path:
    """Creates a FAISS index from database embeddings."""
    ## Extract embed configuration section.
    embed_cfg = config.embed
    model_name = model_name or embed_cfg.model
    index_path = index_path or DEFAULT_INDEX_PATH
    # Make sure the directory exists before saving files.
    _ensure_artifact_dir(index_path)
    # with_suffix() replaces the .faiss extension
    ids_path = index_path.with_suffix(".ids.npy")
    meta_path = index_path.with_suffix(".meta.json")

    # Open a PostgreSQL connection using the configured database URL.
    with psycopg.connect(config.database.url) as conn:
        # Explicitly set the schema to public
        conn.execute("SET search_path TO public")
        # Retrieve all embeddings for the model from the database as NumPy arrays.
        chunk_ids, embeddings = _fetch_embeddings(conn, model_name)

    # embeddings.shape gives (num_vectors, dim).
    # Get number of dimensions in each embedding vector.
    embedding_dim = embeddings.shape[1]

    # Normalize embeddings if cosine similarity is desired
    if config.embed.normalize:
        faiss.normalize_L2(embeddings)
        # Cosine similarity on normalized vectors
        index = faiss.IndexFlatIP(embedding_dim)
        metric_type = "cosine"
    else:
        # Creates a new FAISS index using the L2 (Euclidean distance) metric.
        index = faiss.IndexFlatL2(embedding_dim)
        metric_type = "euclidean"

    # Adds all the embedding vectors to the FAISS index.
    # FAISS internally stores them in contiguous GPU/CPU memory for fast similarity search.
    index.add(embeddings)
    # Save the FAISS index to disk at the given path.
    faiss.write_index(index, str(index_path))
    # Save the array of chunk IDs as a .npy file.
    np.save(ids_path, chunk_ids)
    # Build a small metadata dictionary that summarizes the index.
    meta = {
        "model_name": model_name,
        "embedding_dim": embedding_dim,
        "chunk_count": int(len(chunk_ids)),
        "metric": metric_type,
        "normalized": config.embed.normalize,
        "updated_at": datetime.now(timezone.utc).isoformat() + "Z",
    }
    # Writes the metadata dictionary to disk as a JSON file.
    # json.dumps() converts the Python dictionary into a JSON-formatted string.
    # indent=2 tells Python to print the JSON with two spaces of indentation per nesting level.
    meta_path.write_text(json.dumps(meta, indent=2))
    logging.info(
        "Built FAISS index (%d vectors, dim=%d) -> %s",
        len(chunk_ids),
        embedding_dim,
        index_path,
    )
    return index_path


def load_index(index_path: Path) -> faiss.Index:
    """Loads a saved FAISS index back into memory to later run a query."""
    if not index_path.exists():
        raise FileNotFoundError(f"Index file {index_path} does not exist")
    # FAISS built-in method read_index() loads a previously saved index file.
    # Once loaded, you can call .search()
    return faiss.read_index(str(index_path))


def ensure_index_build(config: PipelineConfig, model_name: str, index_path: Path) -> None:
    """Ensures the index is always up to date with the current embedding model and all required files exist before querying."""
    meta_path = index_path.with_suffix(".meta.json")
    ids_path = index_path.with_suffix(".ids.npy")
    # If one of the required files is missing, rebuild the index.
    needs_rebuild = not index_path.exists() or not ids_path.exists() or not meta_path.exists()
    if not needs_rebuild:
        # If all files do exist, open the JSON file and parse it into a 
        # Python dictionary using json.loads().
        meta = json.loads(meta_path.read_text())

        current_metric = "cosine" if config.embed.normalize else "euclidean"

        # Rebuild if there is a model or metric mismatch.
        if meta.get("model_name") != model_name:
            logging.info(
                "Index built for %s but current model is %s. Rebuilding...",
                meta.get("model_name"),
                model_name,
            )
            needs_rebuild = True
        elif meta.get("metric") != current_metric:
            logging.info(
                "Index built for %s but current metric is %s. Rebuilding...",
                meta.get("metric"),
                current_metric,
            )
            needs_rebuild = True
        else:
            logging.info(
                "FAISS index already up to date (model '%s', metric='%s').", 
                model_name, 
                current_metric
            )
    # Rebuild is any files are missing or wrong model/metric.
    if needs_rebuild:
        build_index(config, model_name=model_name, index_path=index_path)
