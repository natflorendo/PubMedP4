"""
retriever.py

Runs similarity search over FAISS index and PostgreSQL metadata.
"""

from __future__ import annotations
import os
os.environ["TOKENIZERS_PARALLELISM"] = "false" # Done to silence a warning


import logging
from pathlib import Path
from typing import Iterable, List

import numpy as np
import psycopg
from sentence_transformers import SentenceTransformer

from pipeline.config.config import PipelineConfig
from .index_builder import DEFAULT_INDEX_PATH, ensure_index_build, load_index, _ensure_artifact_dir
from .answer_generator import generate_answer


def _fetch_chunk_metadata(conn: psycopg.Connection, chunk_ids: Iterable[int]) -> dict[int, dict]:
    """Fetches text and metadata from a list of given chunk IDs"""
    # Deduplicate list (if there are any).
    chunk_ids = list(set(chunk_ids))
    if not chunk_ids:
        return {}
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT tc.chunk_id, tc.chunk_text, tc.pmid, d.doc_id, d.title
            FROM text_chunks tc
            JOIN documents d ON d.pmid = tc.pmid
            WHERE tc.chunk_id = ANY(%s)
            """,
            (chunk_ids,),
        )
        rows = cur.fetchall()

    # Builds a dictionary with chunk_id as the key
    # and a nested dictionary with the rest of the metadata as its value.
    return {
        row[0]: {
            "chunk_text": row[1],
            "pmid": row[2],
            "doc_id": row[3],
            "title": row[4],
        }
        for row in rows
    }


def _log_query(
        conn: psycopg.Connection, 
        query_text: str, 
        ordered_results: List[dict],
        response_text: str | None = None,
        user_id: int | None = None,
) -> int:
    """Log the query and its retrieved results into the database."""
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO query_logs (query_text, response_text, user_id) VALUES (%s, %s, %s) RETURNING query_id",
            (query_text, response_text, user_id),
        )
        query_id = cur.fetchone()[0]
        # Store document level retrievals in database.
        for result in ordered_results:
            cur.execute(
                "INSERT INTO retrieves (query_id, doc_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (query_id, result["doc_id"]),
            )
    return query_id

# * = All parameters after this point must be passed by keyword, not by position.
# * is a keyword-only seperator.
def search_index(
    config: PipelineConfig,
    query_text: str,
    k: int = 5,
    *,
    model_name: str | None = None,
    index_path: Path | None = None,
    answer_model: str | None = None,
    user_id: int | None = None,
) -> tuple[List[dict], str | None, int | None]:
    """Find and return the top-k most similar text chunks."""
    # Extract embed configuration section.
    embed_cfg = config.embed
    model_name = model_name or embed_cfg.model
    index_path = index_path or DEFAULT_INDEX_PATH
    # Make sure the directory where the index will live exists
    _ensure_artifact_dir(index_path)
    # Rebuild index if missing, incomplete, or outdated compared to the current embedding model.
    ensure_index_build(config, model_name, index_path)

    ids_path = index_path.with_suffix(".ids.npy")
    # Loads all the chunk IDs into a NumPy array.
    chunk_ids = np.load(ids_path)
    index = load_index(index_path)
    logging.info("Loaded FAISS index from %s", index_path)

    # Initialize the embedding model
    model = SentenceTransformer(model_name)
    # Embed the query and convert it to a NumPy array of type 32-bit float.
    query_vec = model.encode([query_text], convert_to_numpy=True, normalize_embeddings=embed_cfg.normalize).astype(
        "float32"
    )
    # index.search() compares the query vector to every vector in the index.
    scores, indices = index.search(query_vec, min(k, len(chunk_ids)))
    # [0] because the pipeline only embeds a single query at a time.
    retrieved_ids = [int(chunk_ids[i]) for i in indices[0]]

    with psycopg.connect(config.database.url) as conn:
        # Explicitly set the schema to public
        conn.execute("SET search_path TO public")
        # Loading the chunks whose IDs were retrieved by FAISS
        metadata = _fetch_chunk_metadata(conn, retrieved_ids)
        ordered_results = []
        # Interpret FAISS scores based on the metric used:
        #  - For L2 (IndexFlatL2): lower distance = higher similarity
        #  - For cosine/inner product (IndexFlatIP): higher score = higher similarity
        for chunk_id, score in zip(retrieved_ids, scores[0]):
            info = metadata.get(chunk_id)
            if not info:
                continue
            ordered_results.append(
                {
                    "chunk_id": chunk_id,
                    "score": float(score),
                    "chunk_text": info["chunk_text"],
                    "pmid": info["pmid"],
                    "doc_id": info["doc_id"],
                    "title": info["title"]
                }
            )

        # Generate answer if model is provided
        answer = None
        query_id = None
        if answer_model:
            answer = generate_answer(query_text, ordered_results, answer_model)
            if answer:
                logging.info("Generated answer with %s:\n%s", answer_model, answer)
            else:
                logging.info("Answer generation skipped or failed.")

        if ordered_results:
                query_id = _log_query(conn, query_text, ordered_results, answer, user_id=user_id)
                logging.info("Logged query: %s (query_id=%d)", query_text, query_id)

    return ordered_results, answer, query_id
