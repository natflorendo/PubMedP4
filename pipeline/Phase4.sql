-- How to run SQL file: psql -d <DATABASE> -f Phase4.sql
--   EX: psql -d pubmedflo -f Phase3.sql
--       psql "$PUBMEDFLO_DB_URL" -f Phase4.sql
-- Clean and Restart Tables: 
--    psql -U nathan -d pubmedflo -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"


-- USERS & ROLES --
CREATE TABLE users (
    -- Strict auto-increment: can’t override unless you say OVERRIDING SYSTEM VALUE
    user_id        BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name           VARCHAR(100) NOT NULL,
    email          VARCHAR(100) UNIQUE NOT NULL,
    password_hash  TEXT NOT NULL,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE admins (
    user_id BIGINT PRIMARY KEY,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE curators (
    user_id BIGINT PRIMARY KEY,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE end_users (
    user_id        BIGINT PRIMARY KEY,
    last_activity  TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- JOURNAL --
CREATE TABLE journals (
    journal_id  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name        VARCHAR(100) NOT NULL
);

-- AUTHOR --
CREATE TABLE authors (
    author_id    BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    author_name  VARCHAR(150) NOT NULL
);

-- PUBMEDARTICLE -- 
CREATE TABLE pubmed_articles (
    pmid              BIGINT PRIMARY KEY,
    title             TEXT NOT NULL,
    citation          TEXT,
    publication_year  INT,
    create_date       DATE,
    doi               VARCHAR(100),
    pmcid             VARCHAR(50),
    nihmsid           VARCHAR(50),

    journal_id        BIGINT,
    FOREIGN KEY (journal_id) REFERENCES journals(journal_id) ON DELETE SET NULL
);

-- DOCUMENT --
CREATE TABLE documents (
    doc_id      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title       TEXT NOT NULL,
    type        VARCHAR(50),
    source_url  TEXT,
    processed   BOOLEAN DEFAULT FALSE,
    added_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Foreign key for the 1-to-N 'adds' relationship
    -- Document needs a curator when created, but if the curator is deleted, the document stays
    added_by    BIGINT,
    FOREIGN KEY (added_by) REFERENCES curators(user_id) ON DELETE SET NULL,

    -- Foreign key for the 1-to-0..1 'describes' relationship
    pmid        BIGINT UNIQUE,
    FOREIGN KEY (pmid) REFERENCES pubmed_articles(pmid) ON DELETE SET NULL
);

-- Junction table for the N-to-N 'write' relationship
-- This is represented by the 'PubMedAuthor' entity
CREATE TABLE pubmed_authors (
    pmid             BIGINT,
    author_id        BIGINT,
    author_order     INT,
    PRIMARY KEY (pmid, author_id),
    FOREIGN KEY (pmid) REFERENCES pubmed_articles(pmid) ON DELETE CASCADE,
    FOREIGN KEY (author_id) REFERENCES authors(author_id) ON DELETE CASCADE
);

CREATE TABLE query_logs (
    query_id        BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    query_text      TEXT,
    response_text   TEXT,
    issued_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    user_id      BIGINT,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Junction table for the N-to-N 'retrieves' relationship
CREATE TABLE retrieves (
    query_id  BIGINT,
    doc_id    BIGINT,
    PRIMARY KEY (query_id, doc_id),
    FOREIGN KEY (query_id) REFERENCES query_logs(query_id) ON DELETE CASCADE,
    FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
);

-- TEXT CHUNKS
CREATE TABLE text_chunks (
    chunk_id       BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pmid           BIGINT NOT NULL,
    chunk_index    INT NOT NULL,
    chunk_text     TEXT NOT NULL,
    start_offset   INT,
    end_offset     INT,
    content_hash   TEXT NOT NULL,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (pmid, chunk_index),
    FOREIGN KEY (pmid) REFERENCES pubmed_articles(pmid) ON DELETE CASCADE
);

-- CHUNK EMBEDDINGS
CREATE TABLE chunk_embeddings (
    embedding_id   BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chunk_id       BIGINT NOT NULL,
    pmid           BIGINT NOT NULL,
    model_name     TEXT NOT NULL,
    embedding_dim  INT NOT NULL,
    embedding      DOUBLE PRECISION[] NOT NULL,
    text_hash      TEXT NOT NULL,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (chunk_id, model_name),
    FOREIGN KEY (chunk_id) REFERENCES text_chunks(chunk_id) ON DELETE CASCADE
);