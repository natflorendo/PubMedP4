/*
 * reset.sql
 *
 * Purpose:
 *   Empties all project tables while keeping schema structure intact.
 *   Also resets ID sequences and cascades through foreign-key dependencies.
 *
 * Usage:
 *   psql "$PUBMEDFLO_DB_URL" -f reset.sql
 *   psql -U nathan -d pubmedflo -f reset.sql
 */

-- TRUNCATE TABLE removes all rows from one or more tables without scanning each row (like DELETE)
-- RESTART IDENTITY resets any auto-incrementing primary keys
BEGIN;

TRUNCATE TABLE
    admins,
    authors,
    chunk_embeddings,
    curators,
    documents,
    end_users,
    journals,
    pubmed_articles,
    pubmed_authors,
    query_logs,
    retrieves,
    text_chunks,
    users
RESTART IDENTITY CASCADE;

COMMIT;

-- Verify emptiness
-- pg_class is a system catalog table in PostgreSQL that contains a row for every table, index, sequence, and view in the database.
SELECT relname AS table_name, reltuples::bigint AS estimated_rows
FROM pg_class
WHERE relkind = 'r'
  AND relname IN (
    'pubmed_articles','pubmed_authors','pubmed_journals',
    'pubmed_citations','documents','curators','users',
    'text_chunks','chunk_embeddings','query_logs','retrieves'
  )
ORDER BY relname;
