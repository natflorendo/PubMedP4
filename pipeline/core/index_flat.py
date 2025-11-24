"""
index_flat.py

Orchastrates FAISS index building, retrieval, and optional answer generation for PubMedFlo chunks.

Note:
 - FAISS = Facebook AI Similarity Search

Usage examples:
  python3 -m core.index_flat --build-only
  python3 -m core.index_flat --query "best treatment for central diabetes insipidus" --k 5
  python3 -m core.index_flat --metric cosine --query "best treatment for central diabetes insipidus" --k 5
  python3 -m core.index_flat --answer --query "What is the treatment for central diabetes insipidus?" --k 5
"""

from __future__ import annotations

import argparse
import logging
from dataclasses import replace 
from pathlib import Path

from pipeline.config.config import PipelineConfig, load_config

from .index_builder import DEFAULT_INDEX_PATH, build_index, ensure_index_build
from .retriever import search_index


def run(
    config: PipelineConfig,
    query: str | None = None,
    k: int = 5,
    answer: bool = False,
    answer_model: str | None = None,
) -> None:
    # If there is a query, search the index, otherwise build the index
    if query:
        llm_model = answer_model or config.generation.llm_model
        results, answer, _ = search_index(
            config,
            query,
            k,
            answer_model=llm_model if answer else None,
        )
        if not results:
            logging.warning("No results returned for query: %s", query)
            return
        logging.info("Top-%d results:", len(results))
        for idx, result in enumerate(results, 1):
            logging.info(
                "#%d score=%.4f pmid=%s title=%s",
                idx,
                result["score"],
                result["pmid"],
                result["title"],
            )
    else:
        # Call this instead of build_index() directly so that the index is only rebuilt when necessary.
        # Can force rebuild with --build-only flag
        ensure_index_build(config, config.embed.model, DEFAULT_INDEX_PATH)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the FAISS indexing and retrieval pipeline. Allows customization of runtime behavior."""
    # The `description` and `help` text will appear if someone runs: python3 -m core.index_flat --help
    parser = argparse.ArgumentParser(description="Build and query FAISS index over chunk embeddings.")
    parser.add_argument(
        "--config",
        default=str(Path(__file__).resolve().parents[1] / "config" / "config.toml"),
        help="Path to config.toml (default: %(default)s)",
    )
    # Optional flag for choosing metric type (cosine or euclidean) to allow for testing with multiple
    # algorithms with minimal change
    parser.add_argument(
        "--metric",
        default=None,
        choices=["cosine", "euclidean"],
        help="Similarity metric override (default: config.toml).",
    )
    # This flag technically isn't necessary, but having it makes the intention more explicit and allows forced rebuilds.
    # action_true makes it so that the parameter automatically toggles a boolean value.
    #  -  If the flag appears, args.build_only = True. If the flag doesn’t appear, args.build_only = False
    parser.add_argument("--build-only", action="store_true", help="Rebuild the FAISS index and exit.")
    parser.add_argument("--query", help="Query text for similarity search.")
    parser.add_argument("--k", type=int, default=5, help="Number of results to return (default: %(default)s)")
    parser.add_argument(
        "--answer",
        action="store_true",
        help="Generate an LLM answer for the query (requires OPENAI_API_KEY).",
    )
    # Allows the ability to use a different LLM model. (model must be available through the OpenAI API)
    parser.add_argument(
        "--llm-model",
        default=None,
        help="LLM model to use when --answer is set (default: value from config.toml)",
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

    # Override metric type if provided via CLI.
    if args.metric:
        # Create a new EmbedConfig with updated normalize flag
        new_embed = replace(config.embed, normalize=(args.metric == "cosine"))
        config = replace(config, embed=new_embed)
        logging.info("Overriding metric type to '%s' via CLI flag.", args.metric)

    # If build only it goes stright into it.
    if args.build_only:
        build_index(config)
    elif args.query:
        run(
            config,
            args.query,
            args.k,
            args.answer,
            args.llm_model,
        )
    else:
        # Fall back is building index, but only rebuild when necessary.
        ensure_index_build(config, config.embed.model, DEFAULT_INDEX_PATH)


if __name__ == "__main__":
    main()
