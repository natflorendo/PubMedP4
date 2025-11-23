from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import psycopg

from pipeline.config.config import PipelineConfig, load_config
from pipeline.core import embed_chunks
from pipeline.core.chunker import chunk_text, normalize_text
from pipeline.core.index_builder import build_index
from pipeline.core.pdf_reader import read_document
from pipeline.utils.db_writer import ensure_pubmed_document_entry, upsert_chunks
from pipeline.utils.metadata_loader import ArticleMetadata, MetadataStore, upload_metadata_to_db


# Structured summary describing a curator upload run.
# frozen=True means it automatically generates an immutable class with an __init__ method.
# (once created, you can’t change its fields)
@dataclass(frozen=True)
class IngestionResult:
    pmid: int             # PubMed ID for the ingested article.
    doc_id: int | None    # Documents table ID if inserted/found, else None.
    title: str            # Title stored for the document.
    chunk_count: int      # Number of chunks created from the document text.
    embedding_count: int  # Number of embeddings generated/stored for the chunks.


class PipelineService:
    """
    Service-layer adapter from the Phase 3 pipeline for the backend.
    `pubmed_pipeline.py` is a CLI/batch orchestrator that crawls a data folder,
    while this class has importable methods to ingest a single uploaded document 
    from the API, and returns a IngestionResult model for HTTP responses.
    """

    def __init__(self, config_path: str | None = None) -> None:
        # Get the path for config.toml used in Phase 3. Need for thigs such as database url, 
        # chunk_size, overlap_ratio, embed model, and more.
        default_config = (
            Path(__file__).resolve().parents[1] / "pipeline" / "config" / "config.toml"
        )
        # Take given config_path when PipelineService is initialized or use the default_config as a fallback.
        self._config_path = config_path or str(default_config)
        self._config: PipelineConfig | None = None


    # @property turns the method into a read-only attribute.
    @property
    def config(self) -> PipelineConfig:
        if self._config is None:
            # Use load_config function to load input sections from config.toml.
            self._config = load_config(self._config_path)
        return self._config


    # * = All parameters after this point must be passed by keyword, not by position.
    # * is a keyword-only seperator.
    def ingest_document(
        self,
        document_path: Path,
        metadata_rows: Sequence[ArticleMetadata],
        *,
        added_by: int | None = None,
    ) -> IngestionResult:
        """
        Run the ingestion pipeline for a single uploaded document.
        Returns metadata about the processed document once embeddings and FAISS index are refreshed.
        """
        # Ingestion requires metadata for the uploaded document.
        if not metadata_rows:
            raise ValueError("Metadata rows are required for ingestion.")

        config = self.config
        # Reads and extracts the entire text from the uploaded PDF/.txt file.
        raw_text = read_document(document_path)
        # Removes extra whitespace and drops non-ASCII characters so chunking is stable
        normalized_text = normalize_text(raw_text)

        # Declare a helper object that knows how to match a metadata row to a document.
        metadata_store = MetadataStore(metadata_rows)
        try:
            # Tries to identify the article for a given file through DOI then looking for text 
            # to the closest match to the document title.
            article = metadata_store.resolve(document_path, normalized_text)
        except LookupError:
            # .resolve(...) was unable to match metadata to a document
            # If there is exactly one row in the CSV, then even if the resolver can’t prove it matches,
            # just assume that row corresponds to that file.
            if len(metadata_rows) == 1:
                article = metadata_rows[0]
            # Otherwise just raise the error given by .resolve(...)
            else:
                raise
        
        chunk_count = 0
        doc_id: int | None = None
        # `with` means that the borrowed connection from the pool is always cleaned up once the block ends and 
        # if an error happens, the connection is still returned to the pool so no open connections leak.
        with psycopg.connect(config.database.url) as conn:
            # Ensures all SQL commands target the public schema.
            conn.execute("SET search_path TO public")
            # Inserts or updates metadata from the CSV into the pubmed_articles metadata table
            upload_metadata_to_db(conn, metadata_rows)
            # Ensures a row exists in the documents table for this PMID. If it exists but title/source URL changed, updates those fields.
            ensure_pubmed_document_entry(conn, article, added_by=added_by)
            # Splits the normalized text into overlapping chunks.
            chunks = chunk_text(
                article.pmid,
                normalized_text,
                config.input.chunk_size,
                config.input.overlap_ratio,
            )
            if not chunks:
                raise ValueError("Uploaded document produced zero chunks after normalization.")
            chunk_count = len(chunks)
            # Upsert chunks into the DB.
            upsert_chunks(conn, chunks)
            row = conn.execute(
                "SELECT doc_id FROM documents WHERE pmid = %s",
                (article.pmid,),
            ).fetchone()
            doc_id = row[0] if row else None
            conn.commit()

        # Generate embeddings for any new chunks and rebuild the FAISS index so
        # they are queryable right away.
        embed_chunks.run(config)
        build_index(config)

        embedding_count = self._count_embeddings(article.pmid)
        return IngestionResult(
            pmid=article.pmid,
            doc_id=doc_id,
            title=article.title,
            chunk_count=chunk_count,
            embedding_count=embedding_count,
        )

    # Helper function to get the embedding_count for IngestionResult.
    def _count_embeddings(self, pmid: int) -> int:
        """Return how many embeddings exist for the current model and pmid."""
        with psycopg.connect(self.config.database.url) as conn:
            conn.execute("SET search_path TO public")
            row = conn.execute(
                """
                SELECT COUNT(*) FROM chunk_embeddings
                WHERE pmid = %s AND model_name = %s
                """,
                (pmid, self.config.embed.model),
            ).fetchone()
            return int(row[0]) if row else 0
