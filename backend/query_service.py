from __future__ import annotations

import os
from pathlib import Path

from pipeline.config.config import PipelineConfig, load_config
from pipeline.core.retriever import search_index


class QueryService:
    """Runs similarity search and optional LLM answers for the API layer."""

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
    def run_query(
        self,
        query_text: str,
        top_k: int = 5,
        *,
        include_answer: bool = True,
        answer_model: str | None = None,
        user_id: int | None = None,
    ) -> dict:
        config = self.config
        # Use given LLM model or fallback to the default in `config.toml`
        llm_model = answer_model or config.generation.llm_model
        # results is the list of retrieved chunks as a dict
        results, answer, query_id = search_index(
            config,
            query_text,
            top_k,
            answer_model=llm_model if include_answer else None,
            user_id=user_id,
        )

        citations = []
        seen_pmids: set[int] = set()
        # Build unique citations from the list of chunk results.
        for result in results:
            pmid = result["pmid"]
            if pmid in seen_pmids:
                continue
            seen_pmids.add(pmid)
            citations.append(
                {
                    "pmid": pmid,
                    "title": result["title"],
                    "doc_id": result["doc_id"],
                }
            )

        return {
            "query_id": query_id,
            "answer": answer,
            "citations": citations,
            "retrieved_chunks": results,
        }
