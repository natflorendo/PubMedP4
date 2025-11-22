"""
pubmed_pipeline.py

Orchestrates entire pipeline to load PDFs, chunk text, generate embeddings, and
build a FAISS index in PostgreSQL.

Usage:
python3 pubmed_pipeline.py --log-level INFO
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from config.config import PipelineConfig, load_config
from core import parse_directory as parse_stage
from core import embed_chunks as embed_stage
from core import index_flat as index_stage


def run(config: PipelineConfig) -> None:
    logging.info("=== Task 1: Parsing & Chunking ===")
    parse_stage.run(config)

    logging.info("=== Task 2: Embedding Generation ===")
    embed_stage.run(config)
    
    logging.info("=== Task 3: Building FAISS Index ===")
    index_stage.run(config)

    logging.info("Pipeline completed successfully.")


def parse_args() -> argparse.Namespace:
    # The `description` and `help` text will appear if someone runs: python3 pubmed_pipeline.py --help
    parser = argparse.ArgumentParser(description="Run parsing + embedding pipeline.")
     # Path(__file__) creates a Path object pointing to the current Python file.
    # .resolve() converts that into an absolute path, resolving any .. or symbolic links.
    # .parent gets the directory that contains this file.
    # /"config"/"config.toml" appends the subdirectory and filename
    # Then convert the Path to a string because argparse expects a plain string.
    parser.add_argument(
        "--config",
        default=str(Path(__file__).resolve().parent / "config" / "config.toml"),
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

# Python idiom that checks whether the file is being run directly or imported as a module (-m).
if __name__ == "__main__":
    main()
