"""
config.py

Loads configuration settings for the PubMedFlo vector pipeline.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
import tomllib

# frozen = true means it automatically generates an immutable class with an __init__ method.
# (once created, you can’t change its fields)
# [database] in toml
@dataclass(frozen=True)
class DatabaseConfig:
    url: str   # Database connection url

# [input] in toml
@dataclass(frozen=True)
class InputConfig:
    raw_dir: Path         # Absolute path that contains raw source files (PDF or text)
    metadata_csv: Path    # Absolute path to the metadata CSV
    chunk_size: int       # Number of tokens per chunk text
    overlap_ratio: float  # Overlap between consecutive chunks (e.g., 0.15 means 15% shared tokens)

# [embed] in toml
@dataclass(frozen=True)
class EmbedConfig:
    model: str       # Name of the embedding model
    batch_size: int  # Number of text chunks processed at once when generating embeddings
    normalize: bool  # Whether to normalize embeddings to unit length (do true for cosine similarity)

# [generation] in toml
@dataclass(frozen=True)
class GenerationConfig:
    llm_model: str  # Default LLM for answer generation

# Combine all smaller configs into a unified structure.
@dataclass(frozen=True)
class PipelineConfig:
    database: DatabaseConfig
    input: InputConfig
    embed: EmbedConfig
    generation: GenerationConfig

# _ signifies it is a private helper function.
def _resolve_path(base: Path, value: str | None) -> Path | None:
    """
    Resolve potential relative or environment-based paths into an absolute Path object.
    Converts relative paths into absolute ones based on the given base directory.
    """
    if value is None:
        return None
    # If the path includes environment variables (like $HOME or ${DATA_DIR}),
    # this replaces them with their real values.
    expanded = os.path.expandvars(value)
    path = Path(expanded)
    if not path.is_absolute():
        # .resolve() converts to a full absolute path
        path = (base / path).resolve()
    return path


def load_config(config_path: str | Path | None = None) -> PipelineConfig:
    """
    Load pipeline configuration from a TOML file. Environment variables are
    substituted per os.path.expandvars on each string value.
    """
    # If no path is given default to config.toml
    if config_path is None:
        # __file__ is the full path of the current python file (e.g. /Users/nathan/CS480/phase3/config.py).
        # Convert to a Path object, then .with_name("config.toml") replaces the file name (config.py) with config.toml.
        config_path = Path(__file__).with_name("config.toml")
    # .resolve() converts to a full absolute path
    config_path = Path(config_path).resolve()
    if not config_path.exists():
        raise FileNotFoundError(f"Config file {config_path} does not exist")

    # `with` means that the file will automatically close once the block ends and 
    # if an error happens during parsing, Python will cleanly close the file.
    # `rb` opens the file in binary mode (read binary).
    with config_path.open("rb") as handle:
        # Read and parse the toml into a nested dictionary.
        raw_config = tomllib.load(handle)
    # Get parent directory of the config file
    # parents[1] goes up 2 levels to get out the config folder
    base_dir = config_path.parents[1]

    # Load [database] section
    db_block = raw_config.get("database", {})
    # Grab contents within section
    env_var = db_block.get("env")
    default_url = db_block.get("default")
    db_url = os.getenv(env_var) if env_var else None
    # If the environment variable wasn’t set, fall back to the TOML default.
    if not db_url:
        db_url = default_url
    # If neither an environment variable nor a default URL were provided, return an error.
    if not db_url:
        raise RuntimeError(
            "Database URL not configured. Set the environment variable specified "
            "under [database].env or provide a [database].default value."
        )
    database = DatabaseConfig(url=db_url)

    # Load [input] section
    input_block = raw_config.get("input", {})
    # Grab contents within section 
    raw_dir = _resolve_path(base_dir, input_block.get("raw_dir", "data/raw"))
    if raw_dir is None:
        raise RuntimeError("input.raw_dir must be configured in config.toml")
    metadata_csv = _resolve_path(base_dir, input_block.get("metadata_csv"))
    if metadata_csv is None:
        raise RuntimeError("input.metadata_csv must be configured in config.toml")
    chunk_size = int(input_block.get("chunk_size", 384))
    overlap_ratio = float(input_block.get("overlap_ratio", 0.15))
    input = InputConfig(
        raw_dir=raw_dir,
        metadata_csv=metadata_csv,
        chunk_size=chunk_size,
        overlap_ratio=overlap_ratio,
    )

    # Load [embed] section
    embed_block = raw_config.get("embed", {})
    # Grab contents within section
    model = embed_block.get("model", "sentence-transformers/all-MiniLM-L6-v2")
    batch_size = int(embed_block.get("batch_size", 16))
    normalize = bool(embed_block.get("normalize", False))
    embed = EmbedConfig(model=model, batch_size=batch_size, normalize=normalize)

    # Load [generation] section
    generation_block = raw_config.get("generation", {})
    # Grab contents within section
    llm_model = generation_block.get("llm_model", "gpt-4o-mini")
    generation = GenerationConfig(llm_model=llm_model)

    return PipelineConfig(database=database, input=input, embed=embed, generation=generation)
