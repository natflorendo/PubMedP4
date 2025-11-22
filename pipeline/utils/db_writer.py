"""
db_writer.py

Handles database interactions related to text chunking and document tracking.
"""

import psycopg
import logging
from core.chunker import Chunk
from utils.metadata_loader import ArticleMetadata


def ensure_pubmed_document_entry(conn: psycopg.Connection, article: ArticleMetadata) -> None:
    """Ensure a PubMed-linked document entry exists in the `documents` table."""
    pmid = article.pmid
    title = article.title or f"PMID {pmid}"
    # Insert a new PubMed document or update the existing one only if title, type, or source_url differ.
    # Ensures a single up-to-date record per PMID while avoiding redundant updates.
    conn.execute(
        """
        INSERT INTO documents (title, type, source_url, processed, added_by, pmid)
        VALUES (%(title)s, %(type)s, %(source_url)s, FALSE, NULL, %(pmid)s)
        ON CONFLICT (pmid) DO UPDATE
        SET title = EXCLUDED.title,
            type = EXCLUDED.type,
            source_url = EXCLUDED.source_url
        WHERE documents.title IS DISTINCT FROM EXCLUDED.title
            OR documents.type IS DISTINCT FROM EXCLUDED.type
            OR documents.source_url IS DISTINCT FROM EXCLUDED.source_url
        """,
        {
            "title": title,
            "type": "pubmed_text",
            "source_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            "pmid": pmid,
        },
    )


def upsert_chunks(conn: psycopg.Connection, chunks: list[Chunk]) -> None:
    """upsert new or modified normalized text chunks for a specific PubMed article into the database."""
    if not chunks:
        return
    # All chunks in the list belong to the same article. Grab the pmid from the first chunk.
    pmid = chunks[0].pmid

    # Fetch current chunk indicies in DB into a set
    existing_indices = {
        row[0]
        for row in conn.execute(
            "SELECT chunk_index FROM text_chunks WHERE pmid = %s",
            (pmid,),
        )
    }

    # Set of all chunk_index values from the new chunk list.
    new_indices = {chunk.chunk_index for chunk in chunks}

    with conn.cursor() as cur:
        # `executemany()` runs the same SQL command repeatedly for many rows
        # For ON CONFLICT, if a row with the same (pmid, chunk_index) already exists, perform an update
        # but only update when the content actually changed (`WHERE text_chunks.content_hash IS DISTINCT FROM EXCLUDED.content_hash`).
        cur.executemany(
            """
            INSERT INTO text_chunks (pmid, chunk_index, chunk_text, start_offset, end_offset, content_hash)
            VALUES (%(pmid)s, %(chunk_index)s, %(chunk_text)s, %(start_offset)s, %(end_offset)s, %(content_hash)s)
            ON CONFLICT (pmid, chunk_index)
            DO UPDATE SET
                chunk_text = EXCLUDED.chunk_text,
                start_offset = EXCLUDED.start_offset,
                end_offset = EXCLUDED.end_offset,
                content_hash = EXCLUDED.content_hash,
                created_at = CURRENT_TIMESTAMP
            WHERE text_chunks.content_hash IS DISTINCT FROM EXCLUDED.content_hash
            """,
            [
                {
                    "pmid": chunk.pmid,
                    "chunk_index": chunk.chunk_index,
                    "chunk_text": chunk.text,
                    "start_offset": chunk.start_offset,
                    "end_offset": chunk.end_offset,
                    "content_hash": chunk.content_hash,
                }
                for chunk in chunks
            ],
        )

        # rowcount is a psycopg function that keeps track of how many total rows were affected across all iterations.
        affected = cur.rowcount
        logging.info("Inserted/updated %d chunks for PMID %s", affected, pmid)

    # Remove chunks in the DB, but not in the new list
    # Set difference operator in Python (-)
    stale_indices = existing_indices - new_indices
    if stale_indices:
        conn.execute(
            "DELETE FROM text_chunks WHERE pmid = %s AND chunk_index = ANY(%s)",
            (pmid, list(stale_indices)),
        )
        logging.info("Removed %d stale chunks for PMID %s", len(stale_indices), pmid)
    # Mark the document as processed
    conn.execute("UPDATE documents SET processed = TRUE WHERE pmid = %s", (pmid,))
