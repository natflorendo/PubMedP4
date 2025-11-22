"""
metadata_parser.py

Handles parsing of PubMed metadata stored in CSV format.
"""

from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# Allow dates with either / or -
DATE_FORMATS = ("%Y/%m/%d", "%Y-%m-%d")

# frozen=True means it automatically generates an immutable class with an __init__ method.
# (once created, you can’t change its fields)
@dataclass(frozen=True)
class ArticleMetadata:
    pmid: int                     # PubMed ID of article
    title: str                    # Article title
    authors: tuple[str, ...]      # All authors of a article
    citation: str | None          # Citation text for the paper
    first_author: str | None
    journal_name: str | None      # Journal the article was published
    publication_year: int | None
    create_date: str | None       # Date the record was created in PubMed
    pmcid: str | None             # Alternate ID stored by PubMed
    nihmsid: str | None           # Another optional ID stored by PubMed
    doi: str | None               # Permanent global identifier for the paper.


def _parse_date(value: str | None) -> str | None:
    """Attempt to parse a date string into ISO format (YYYY-MM-DD)."""
    if not value:
        return None
    # remove leading or trailing spaces
    cleaned = value.strip()
    for fmt in DATE_FORMATS:
        try:
            # Attempt to convert to datetime object, then date, then ISO 8601 format
            return datetime.strptime(cleaned, fmt).date().isoformat()
        except ValueError:
            # fails if format didn't match
            continue
    # If no format matched, emit a warning
    logging.warning(f"Could not parse date value: '{value}'")
    return None


def _parse_int(value: str | None) -> int | None:
    """Attempt to convert a string to an integer."""
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        logging.warning(f"Could not parse integer value: '{value}'")
        return None


# Return a tuple rather than a list because it is immutable
def _parse_authors(value: str | None) -> tuple[str, ...]:
    """Parse a comma-separated list of author names from a CSV field into an immutable tuple."""
    if not value:
        return tuple()
    # Get list of author names seperated by commas.
    # First strip() gets rid of leading/trailing whitespace.
    # Second strip removes trailing periods (e.g., "McFarlane SI." -> "McFarlane SI")
    parts = [segment.strip().strip(".") for segment in value.split(",")]
    # None removes any empty strings ("") that may have been stored in parts
    return tuple(filter(None, parts))


def load_metadata_rows(csv_path: Path) -> list[ArticleMetadata]:
    """Load and parse article metadata records from a CSV file into structured ArticleMetadata objects."""
    # Verify the path actually points to a file.
    if not csv_path.exists():
        raise FileNotFoundError(f"Metadata CSV {csv_path} does not exist.")

    # In-memory representation of the CSV data.
    # Okay for now since we only process 30 documents at most for this project.
    # Provides more simplicity compared to streaming it line by line.
    rows: list[ArticleMetadata] = []

    # `with` means that the file will automatically close once the block ends and 
    # if an error happens during parsing, Python will cleanly close the file.
    # `r` opens the file for reading
    # `newline=""` avoids problems with line endings
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        # Reads the CSV file row by row and returns each as a dictionary.
        reader = csv.DictReader(handle)
        for row in reader:
            # Try to read the PMID column and convert it to an integer.
            # If the field is missing, skip the row.
            try:
                # Don't use _parse_int() her because the helper already catches ValueError
                pmid = int(row["PMID"])
            except (KeyError, TypeError, ValueError) as e:
                logging.warning(f"Skipping row due to invalid PMID: {row.get('PMID')} ({e})")
                continue
            # If PMID successfully converted to an integer, created structured ArticleMetadata object.
            rows.append(
                ArticleMetadata(
                    pmid=pmid,
                    title=(row.get("Title") or "").strip() or f"PMID {pmid}",
                    authors=_parse_authors(row.get("Authors")),
                    citation=(row.get("Citation") or "").strip() or None,
                    first_author=(row.get("First Author") or "").strip() or None,
                    journal_name=(row.get("Journal/Book") or "").strip() or None,
                    publication_year=_parse_int(row.get("Publication Year")) or None,
                    create_date=_parse_date(row.get("Create Date")) or None,
                    pmcid=(row.get("PMCID") or "").strip() or None,
                    nihmsid=(row.get("NIHMS ID") or "").strip() or None,
                    doi=(row.get("DOI") or "").strip().lower() or None,
                )
            )
    if not rows:
        raise RuntimeError(f"No usable rows found in metadata CSV {csv_path}")
    return rows
