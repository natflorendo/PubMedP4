"""
chunker.py

Utilities for normalizing text and generating overlapping chunks.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Iterator

# frozen=True means it automatically generates an immutable class with an __init__ method.
# (once created, you can’t change its fields)
@dataclass(frozen=True)
class Chunk:
    pmid: int          # PubMed ID of article chunk belongs to
    chunk_index: int   # Sequential index that identifies the chunks position in a document
    text: str          # text of the chunk
    start_offset: int  # starting character position in the document
    end_offset: int    # ending character position in the document
    content_hash: str  # SHA-256 hash of the chunk’s text (useful for detecting changes/duplicates)


def normalize_text(raw_text: str) -> str:
    """
    Remove extra whitespace and drop non-ASCII characters to ensure
    consistent tokenization across all documents.
    """
    # Converts the input string into bytes dropping any characters that can’t be represented in ASCII.
    # Then decodes back to a string.
    ascii_text = raw_text.encode("ascii", "ignore").decode("ascii", errors="ignore")
    # Uses a regular expression \s+ (Matches to any whitespace sequence: spaces, tabs, or newlines)
    # and replaces them with a single space
    collapsed = re.sub(r"\s+", " ", ascii_text)
    # Remove any leftover spaces at the start or end
    return collapsed.strip()

# match is a piece of text that fits what the regular expression is looking for.
def _get_token_spans(text: str) -> Iterator[re.Match[str]]:
    """
    Find every word (group of non-space characters) in the text.
    This is needed because it makes it easier to cut at word-aligned boundaries when creating chunks.
    """
    # Iterate over all runs of non-whitespace characters (\S+)
    return re.finditer(r"\S+", text)


def chunk_text(
    pmid: int,
    text: str,
    chunk_size: int = 384,
    overlap_ratio: float = 0.15,
) -> list[Chunk]:
    """
    Split normalized text into overlapping windows. Each chunk stores offsets
    and a stable hash for deduplication later.
    """
    # Stores a list of the start/end positions of every word.
    spans = list(_get_token_spans(text))
    if not spans:
        return []

    # Extracts the text of each token
    tokens = [text[match.start() : match.end()] for match in spans]

    # Calculates how far forward to move before starting the next chunk
    step = max(1, int(chunk_size * (1 - overlap_ratio)))

    def build_chunk(start_index: int, chunk_index: int) -> Chunk | None:
        # If the slice end exceeds the token length, Python automatically goes to the end of the list.     
        window = tokens[start_index : start_index + chunk_size]
        if not window:
            return None
        # Get first and last tokens.
        start_offset = spans[start_index].start()
        end_offset = spans[start_index + len(window) - 1].end()
        # Joins all the token strings together with single spaces to rebuild the text for that chunk.
        chunk_text_str = " ".join(window)
        # Create a SHA-256 hash of the chunk’s text and turn the binary fingerprint into a readable string with `hexdigest()`.
        content_hash = hashlib.sha256(chunk_text_str.encode("utf-8")).hexdigest()
        return Chunk(
            pmid=pmid,
            chunk_index=chunk_index,
            text=chunk_text_str,
            start_offset=start_offset,
            end_offset=end_offset,
            content_hash=content_hash,
        )

    # Create a list of chunks
    chunks = []
    # start from 0 and increase by step each time
    for chunk_idx, start_idx in enumerate(range(0, len(tokens), step)):
        chunk = build_chunk(start_idx, chunk_idx)
        if chunk is not None:
            chunks.append(chunk)
    
    return chunks

# When this module is imported with a wildcard (*), only export these four names
__all__ = ["Chunk", "chunk_text", "normalize_text"]
