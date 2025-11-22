"""
pdf_reader.py

Utility functions for extracting text content from PDF documents.
"""

from __future__ import annotations

from pathlib import Path

from PyPDF2 import PdfReader


def read_pdf(path: Path) -> str:
    """
    Extract text from the provided PDF using PyPDF2.
    Raises ValueError if no text was processed.
    """
    # Allows you to access its pages via `reader.pages`
    reader = PdfReader(str(path))
    pages = []
    for page in reader.pages:
        text = page.extract_text() or ""
        # Removes leading and trailing whitespace, newlines, or tabs.
        text = text.strip()
        if text:
            pages.append(text)
    # Join all the non-empty page texts together into one large string, separating pages with newlines.
    content = "\n".join(pages).strip()
    if not content:
        raise ValueError(f"No text extracted from {path}")
    return content


def read_document(path: Path) -> str:
    """
    Read text content from a document. PDF files are parsed with read_pdf,
    plain-text files are read directly.
    """
    
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return read_pdf(path)
    if suffix == ".txt":
        return path.read_text(encoding="utf-8")
    raise ValueError(f"Unsupported file type: {suffix}")
