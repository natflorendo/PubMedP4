-- init.sql
-- Bootstrap the Phase 4 authentication/authorization tables plus
-- the document + query logging tables needed by the backend API.
-- Usage: psql "$PUBMEDFLO_DB_URL" -f init.sql
-- BEGIN; ... COMMIT; wraps the whole schema setup in a single transaction.
--   - Either the entire schema in init.sql is created successfully or none of it is.

BEGIN;

CREATE TABLE IF NOT EXISTS roles (
    role_id     SERIAL PRIMARY KEY,
    role_name   VARCHAR(50) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    user_id       BIGSERIAL PRIMARY KEY,
    name          VARCHAR(100) NOT NULL,
    email         VARCHAR(100) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_roles (
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    role_id INT NOT NULL REFERENCES roles(role_id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, role_id)
);

CREATE TABLE IF NOT EXISTS documents (
    doc_id     BIGSERIAL PRIMARY KEY,
    title      TEXT NOT NULL,
    type       VARCHAR(50),
    source_url TEXT,
    processed  BOOLEAN DEFAULT FALSE,
    added_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    added_by   BIGINT REFERENCES users(user_id) ON DELETE SET NULL,
    pmid       BIGINT UNIQUE
);

CREATE TABLE IF NOT EXISTS query_logs (
    query_id      BIGSERIAL PRIMARY KEY,
    query_text    TEXT,
    response_text TEXT,
    issued_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id       BIGINT REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS retrieves (
    query_id BIGINT REFERENCES query_logs(query_id) ON DELETE CASCADE,
    doc_id   BIGINT REFERENCES documents(doc_id) ON DELETE CASCADE,
    PRIMARY KEY (query_id, doc_id)
);

COMMIT;
