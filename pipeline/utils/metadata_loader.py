"""
metadata_loader.py

Central import file that re-exports metadata functions and classes.
"""

from __future__ import annotations

# The leading dot means import from another module inside the same package.
# Without the dot, Python interprets it as import a top-level module.
from .metadata_parser import ArticleMetadata, load_metadata_rows
from .metadata_sync import upload_metadata_to_db
from .metadata_lookup import MetadataStore

# When this module is imported with a wildcard (*), only export these four names
__all__ = [
    "ArticleMetadata",
    "load_metadata_rows",
    "upload_metadata_to_db",
    "MetadataStore",
]
