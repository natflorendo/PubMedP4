"""
metadata_lookup.py

Matches document text to their corresponding ArticleMetadata.

Notes:
 - There are three resolution methods:
    1. _match_doi_token - Finds a DOI fragment in normalized text (partial match without punctuation).
    2. _match_doi_literal - Finds an exact DOI string match (lowercased, unmodified form).
    3.  _match_title - Falls back to approximate title matching when DOI data is missing.
 - All methods only analyze the first <MAX_TEXT_WINDOW> characters within the document.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from .metadata_parser import ArticleMetadata

# `re.compile() pre-compiles the regex so it runs faster later when reused repeatedly.`
#  `re.IGNORECASE` is case insensitive matching.
# Regex Breakdown:
# - `\b` = Word boundary.
# - `10\.` = DOI prefix is "10.".
# - `\d{4,6}` = 4–6 digits after "10." prefix.
# -  `/` = Slash seperating prefix from suffix.
# - `[-._;()/:A-Za-z0-9]` = Valid DOI suffix characters (letters, numbers, punctuation).
# - `+` = One or more.
DOI_PATTERN = re.compile(r"\b10\.\d{4,6}/[-._;()/:A-Za-z0-9]+\b", re.IGNORECASE)
# How many characters of a document’s text to scan when searching for PMIDs or DOIs
MAX_TEXT_WINDOW = 20_000


def _normalize_for_match(value: str) -> str:
    """
    Normalizes text for comparison. Helps match titles or DOIs even if they differ by punctuation, spacing, or case.
    """
    # Convert the string to lowercase. Use regex substitution to remove any character that isn’t a lowercase letter or digit.
    # `[^a-z0-9]` = anything not a–z or 0–9.
    return re.sub(r"[^a-z0-9]", "", value.lower())


class MetadataStore:
    """Lookup helper to map filenames or document text to metadata rows."""

    def __init__(self, articles: Iterable[ArticleMetadata]) -> None:
        """Set up fast lookup tables for metadata."""
        # Accepts any iterable (list, tuple, etc.) since we only need to loop once
        # and immediately convert it to a list.
        self._articles = list(articles)
        # Dictionary mapping each article’s DOI string to the full ArticleMetadata object.
        self._by_doi = {
            article.doi.strip().lower(): article
            for article in self._articles
            if article.doi
        }
        # Dictionary mapping each article’s NORMALIZED DOI string to the full ArticleMetadata object.
        # Helps match DOIs distorted in extracted PDF text.
        self._doi_tokens = {
            _normalize_for_match(article.doi): article
            for article in self._articles
            if article.doi
        }
        # Dictionary mapping each article’s normalized title to the full ArticleMetadata object.
        self._title_tokens = [
            (_normalize_for_match(article.title), article)
            for article in self._articles
            if article.title
        ]
        # Sort the list of (normalized_titles, article) pairs by title length in descending order.
        # Descending order because it should try to match the most specific (longest) titles first before more generic ones.
        self._title_tokens.sort(key=lambda pair: len(pair[0]), reverse=True)

    # Uncomment print lines (87, 99, 125) to view which function successfully resolves
    # 1 document gets resolved through this function
    def _match_doi_token(self, normalized: str) -> ArticleMetadata | None:
        """Checks if a normalized DOI substring (no punctuation) appears in the normalized text."""
        for token, article in self._doi_tokens.items():
            # If normalized DOI token appears in the normalized text, return the article
            if token and token in normalized:
                # print(f"[RETURN] Resolved token doi: ${token}")
                return article
        return None

    # 14 documents get resolved through this function
    def _match_doi_literal(self, lowered: str) -> ArticleMetadata | None:
        """
        Finds if the raw lowercase DOI text is directly present in the file text.
        """
        for doi_raw, article in self._by_doi.items():
            # If DOI appears in the lowered text, return the article
            if doi_raw and doi_raw in lowered:
                # print(f"[RETURN] Resolved doi: ${doi_raw}")
                return article
        return None

    # 5 documents get resolved through this function
    def _match_title(self, normalized: str, penalty: float = 0.01) -> ArticleMetadata | None:
        """Finds the article whose title best appears in the text."""
        best_article: ArticleMetadata | None = None
        best_score = float("-inf")
        for token, article in self._title_tokens:
            if not token:
                continue
            # Look for normalized title in the normalized document text and store starting index.
            pos = normalized.find(token)
            # Skip to next title if not found
            if pos == -1:
                continue
            # Compute a heuristic score where longer matches score higher
            # and titles appearing later in the text get a small penalty.
            score = len(token) - penalty * pos
            # Update best match
            if score > best_score:
                best_article = article
                best_score = score
        # print(f"[RETURN] Matched title: {best_article}")
        return best_article

    def _resolve_by_text(self, text: str | None) -> ArticleMetadata | None:
        """Try to match metadata based on the document’s content."""
        if not text:
            return None
        window = text[:MAX_TEXT_WINDOW]
        lowered = window.lower()

        # Look for exact match to DOI in lowered text first
        doi_literal = self._match_doi_literal(lowered)
        if doi_literal:
            return doi_literal
        
        # Then check for noramalized DOI in normalized text
        normalized = _normalize_for_match(window)
        doi_token = self._match_doi_token(normalized)
        if doi_token:
            return doi_token
        
        # Final fallback looks for normalized title in normalized text
        return self._match_title(normalized)

    def resolve(self, document_path: Path, text: str | None = None) -> ArticleMetadata:
        """Public method that tries to identify the article for a given file."""
        text_match = self._resolve_by_text(text)
        if text_match:
            return text_match
        raise LookupError(
            f"Unable to resolve metadata for '{document_path.name}'. "
            "Ensure the filename or document content includes a PMID/DOI or recognizable title."
        )
