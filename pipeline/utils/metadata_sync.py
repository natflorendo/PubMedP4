"""
metadata_sync.py

Handles database synchronization of parsed PubMed metadata with PostgreSQL.
"""

from __future__ import annotations

from typing import Sequence

import psycopg

from .metadata_parser import ArticleMetadata


def _get_or_create(conn: psycopg.Connection, query: str, insert: str, value: str) -> int:
    """Check if record already exists. If not, create row and return ID, or just return the ID."""
    existing = conn.execute(query, (value,)).fetchone()
    if existing:
        return existing[0]
    return conn.execute(insert, (value,)).fetchone()[0]


def _ensure_journals_table(conn: psycopg.Connection, name: str | None) -> int | None:
    """
    Find an existing journal’s ID by name, or insert a new row with that name and return its new journal_id.
    """
    if not name:
        return None
    return _get_or_create(
        conn,
        "SELECT journal_id FROM journals WHERE name = %s",
        "INSERT INTO journals (name) VALUES (%s) RETURNING journal_id",
        name,
    )


def _ensure_authors_table(conn: psycopg.Connection, name: str) -> int:
    """
    Find an existing author’s ID by name, or insert a new row with that name and return its new author_id.
    """
    return _get_or_create(
        conn,
        "SELECT author_id FROM authors WHERE author_name = %s",
        "INSERT INTO authors (author_name) VALUES (%s) RETURNING author_id",
        name,
    )


# Sequence can be a list, tuple or something else (as long as you can iterate through it and access elements by index)
def upload_metadata_to_db(
    conn: psycopg.Connection, articles: Sequence[ArticleMetadata]
) -> None:
    """Upsert pubmed_articles, journals, authors, and pubmed_authors from CSV rows."""
    for article in articles:
        # Find the existing journal in the journals table, or insert it if missing, and return its journal_id.
        journal_id = _ensure_journals_table(conn, article.journal_name)
         # For ON CONFLICT, if a row already exists, update it with new data.
         # Used named placeholders because there is a lot of fields
        conn.execute(
            """
            INSERT INTO pubmed_articles (
                pmid, title, citation, publication_year, create_date, doi, pmcid, nihmsid, journal_id
            )
            VALUES (%(pmid)s, %(title)s, %(citation)s, %(publication_year)s, %(create_date)s,
                    %(doi)s, %(pmcid)s, %(nihmsid)s, %(journal_id)s)
            ON CONFLICT (pmid) DO UPDATE
            SET title = EXCLUDED.title,
                citation = EXCLUDED.citation,
                publication_year = EXCLUDED.publication_year,
                create_date = EXCLUDED.create_date,
                doi = EXCLUDED.doi,
                pmcid = EXCLUDED.pmcid,
                nihmsid = EXCLUDED.nihmsid,
                journal_id = EXCLUDED.journal_id
            """,
            {
                "pmid": article.pmid,
                "title": article.title,
                "citation": article.citation,
                "publication_year": article.publication_year,
                "create_date": article.create_date,
                "doi": article.doi,
                "pmcid": article.pmcid,
                "nihmsid": article.nihmsid,
                "journal_id": journal_id,
            },
        )


        # Build new author_ids from the metadata
        # Set that gets current author_ids from DB
        existing_ids = {
            row[0]
            for row in conn.execute(
                "SELECT author_id FROM pubmed_authors WHERE pmid = %s",
                (article.pmid,)
            )
        }

        # Build new author_ids from the metadata
        new_ids = set()
        # Iterate through each author name in article.authors and store the author's position (order)
        for order, author_name in enumerate(article.authors, start=1):
            # Find the existing author in the authors table, or insert it if missing, and return its author_id.
            # Used positional placeholders here because it's a smaller parameter list.
            author_id = _ensure_authors_table(conn, author_name)
            new_ids.add(author_id)

            conn.execute(
                """
                INSERT INTO pubmed_authors (pmid, author_id, author_order)
                VALUES (%s, %s, %s)
                ON CONFLICT (pmid, author_id) DO UPDATE
                SET author_order = EXCLUDED.author_order
                """,
                (article.pmid, author_id, order),
            )

        # Remove authors that were present but are no longer in metadata
        # Set difference operator in Python (-)
        stale_ids = existing_ids - new_ids
        if stale_ids:
            conn.execute(
                "DELETE FROM pubmed_authors WHERE pmid = %s AND author_id = ANY(%s)",
                (article.pmid, list(stale_ids)),
            )
