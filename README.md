# CS 480 - Phase 4: PubMedFlo Full System Integration

**Name:** Nathan Florendo

---

## Table of Contents

* [Overview](#overview)
* [Project Description](#project-description)
* [Architecture](#architecture)
* [Source Files Summary](#source-files-summary)
* [Supporting Files & Directories](#supporting-files--directories)
* [Dependencies & Setup](#dependencies--setup)
* [Running the System](#running-the-system)
* [Phase 4 Persona Walkthroughs](#phase-4-persona-walkthroughs)
* [Example Queries](#example-queries)
* [Verification and Tests](#verification-and-tests)
* [Results and Outputs](#results-and-outputs)

---

## Overview
At a ***high-level***, this phase delivers a **complete question‑answering system**. Phase 3 built the vector pipeline (chunking, embeddings, FAISS); Phase 4 layers on the FastAPI backend, auth/roles, curator and end-user routes, and the integrated SQL schema. The backend exposes authentication, role-based access, curator document ingestion, and an end-user `/query` endpoint that returns LLM answers with citations. All data persists in PostgreSQL (documents, chunks, embeddings, users, query logs) so the server can restart without losing functionality.

---

## Project Description
This section summarizes how the integrated system works end to end:

* **Authentication & Roles** – Users sign up/login with hashed passwords. Admins/curators/end-users are tracked in SQL tables defined in `pipeline/Phase4.sql`. JWT bearer tokens protect every route.
* **Curator Ingestion Pipeline** – Curators upload PDFs + metadata (CSV or manual fields). The server reuses the Phase 3 chunking + embedding pipeline, updates Postgres, and refreshes the FAISS index so new documents are instantly searchable.
* **Vector Retrieval + LLM Answering** – `/query` encodes the user’s prompt, runs FAISS search, fetches chunk metadata, and optionally calls `gpt-4o-mini` to synthesize an answer with inline `[PMID #######]` citations.
* **Logging & Auditing** – Each query is stored in `query_logs` along with retrieved document IDs. Deleting a user cascades through their query history per the schema.
* **Persistence** – Because everything is written to PostgreSQL (and FAISS artifacts live on disk), curator uploads and user accounts survive restarts.

---

## Architecture
The system now has two layers:

1. **Vector Pipeline (Phase 3)** – `pipeline/core/*`, `pipeline/utils/*`, and `pipeline/pubmed_pipeline.py` still parse PDFs, chunk text, embed, and write FAISS indices.
2. **FastAPI Backend (Phase 4)** – `backend/*` wraps the pipeline in REST endpoints:
   * `auth.py` – signup/login/me, password hashing, JWT issuance.
   * `admin.py` – list/update/delete users, admin-only dependency.
   * `curator.py` – upload documents, list curated corpus, delete own documents (admins can delete any).
   * `query.py` – `/query` endpoint returning answer + citations + retrieved chunks.
   * `query_service.py` – orchestrates retrieval and answer formatting.
   * `repository.py` – connection pooling + CRUD helpers for users/documents.
   * `app.py` – FastAPI entrypoint, CORS configuration, lifespan/pool wiring.

---

## Source Files Summary

* **backend/app.py** – Creates the FastAPI app, sets CORS, registers auth/admin/curator/query routers, manages DB pool lifecycle.
* **backend/auth.py** – Signup/login/me logic (bcrypt hashing, JWT creation/verification, role guards).
* **backend/admin.py** – Admin-only endpoints for listing and editing users (`GET/PUT/DELETE /admin/users`).
* **backend/curator.py** – Handles uploads (CSV or form metadata), stores documents, and exposes `GET/DELETE /curator/documents` with chunk/embedding stats.
* **backend/query.py** – `POST /query` endpoint that returns `answer`, `citations`, and `retrieved_chunks` for authenticated users.
* **backend/query_service.py** – Calls the shared retriever to run FAISS search, generate answers, and format citations.
* **backend/repository.py** – Connection pool + repositories for users and documents (role assignment, document stats, secure deletion checks).
* **pipeline/core/** – Unchanged vector pipeline modules (chunking, embeddings, FAISS index, retriever, answer generator).
* **pipeline/utils/** – Metadata parsing/syncing helpers, database writers for chunks/documents.
* **pipeline/pubmed_pipeline.py** – Rebuilds the index offline by reusing the same ingestion steps used by the backend.

---

## Supporting Files & Directories

* **Phase4.sql** – Final relational schema (users/roles, documents, chunks, embeddings, query logs, retrieves).
* **reset.sql** – Truncates all project tables while keeping the schema.
* **requirements.txt** – Includes FastAPI, Uvicorn, JWT/passlib, OpenAI, psycopg, sentence-transformers, FAISS.
* **.env.example** – Template for `PUBMEDFLO_DB_URL`, `PUBMEDFLO_SECRET`, `OPENAI_API_KEY`, etc.
* **tests/** – Contains `test_curator_routes.py`, which uses FastAPI’s TestClient to exercise the new curator listing/deletion endpoints.
* **artifacts/** – FAISS index + metadata generated by the pipeline.

---

## Dependencies & Setup

```bash
cd phase4
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

### Initialize the Database Schema

```bash
psql "$PUBMEDFLO_DB_URL" -f pipeline/Phase4.sql
```

### Environment Variables

```bash
cp .env.example .env
```
Then edit `.env`:
```bash
PUBMEDFLO_DB_URL="postgresql://postgres:postgres@localhost:5432/pubmedflo"
PUBMEDFLO_SECRET="dev-secret-change-me"
PUBMEDFLO_JWT_ALGORITHM="HS256"
PUBMEDFLO_TOKEN_TTL="60"
PUBMEDFLO_CORS_ORIGINS="http://localhost:3000"
OPENAI_API_KEY="sk-your-key"   # optional; required for answer generation
```

---

## Running the System

1. **Build or refresh the FAISS artifacts (optional, Phase 3 pipeline)**
   ```bash
   python3 -m pipeline.pubmed_pipeline --log-level INFO
   ```
2. **Start the FastAPI backend**
   ```bash
   uvicorn backend.app:app --reload
   ```
3. **Use curl/Postman** (examples below) or integrate with a frontend/UI.

---

## Phase 4 Persona Walkthroughs

These curl commands mirror the grading scenarios. Replace emails/passwords/file paths with your own values and set `TOKEN` to the JWT returned from `/login`.

### 1. Signup & Login
```bash
# Signup (assign admin + curator roles)
curl -X POST http://localhost:8000/signup \
     -H "Content-Type: application/json" \
     -d '{"name":"Alice","email":"alice@example.com","password":"SuperSecret1!","roles":["admin","curator"]}'

# Login to receive an access token (OAuth2 password grant)
curl -X POST http://localhost:8000/login \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d 'username=alice@example.com&password=SuperSecret1!'

TOKEN="<paste access_token>"
```

### 2. Admin List & Edit Users
```bash
# List every user
curl http://localhost:8000/admin/users \
     -H "Authorization: Bearer $TOKEN"

# Promote user_id=2 to curator + end_user
curl -X PUT http://localhost:8000/admin/users/2 \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"roles":["curator","end_user"]}'
```

### 3. Curator Upload/List/Delete
```bash
# Upload a PDF with companion metadata CSV
curl -X POST http://localhost:8000/curator/upload \
     -H "Authorization: Bearer $TOKEN" \
     -F "document=@/path/to/doc.pdf;type=application/pdf" \
     -F "metadata_csv=@/path/to/metadata.csv"

# List curator-managed documents & stats
curl http://localhost:8000/curator/documents \
     -H "Authorization: Bearer $TOKEN"

# Delete a document you uploaded (admins can delete any doc)
curl -X DELETE http://localhost:8000/curator/documents/<DOC_ID> \
     -H "Authorization: Bearer $TOKEN"
```

### 4. End-User Query (answer + citations)
```bash
curl -X POST http://localhost:8000/query \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"query":"best therapy for central diabetes insipidus","k":5,"include_answer":true}'
```
The response contains:
* `answer` – optional LLM summary (requires `OPENAI_API_KEY`).
* `citations` – unique PMIDs + document IDs.
* `retrieved_chunks` – text snippets with scores.
* `query_id` – row in `query_logs` for auditing.

### 5. Persistence Check
1. Upload a document.
2. Query for a passage in that document; note the `query_id`.
3. Restart the API and re-run the query—the document remains searchable, proving persistence.

---

## Example Queries
* “best treatment for central diabetes insipidus”
* “How to diagnose central diabetes insipidus”
* “What fluid management strategies are recommended for DI?”
* “Founding of the US” *(returns no answer; demonstrates graceful handling of off-topic queries)*

These can be run via the CLI (`python3 -m core.index_flat --query ...`) or the REST API (`POST /query`).

---

## Verification and Tests

* **Database sanity checks**
  ```bash
  psql "$PUBMEDFLO_DB_URL" -c "SELECT COUNT(*) FROM users;"
  psql "$PUBMEDFLO_DB_URL" -c "SELECT COUNT(*) FROM documents;"
  psql "$PUBMEDFLO_DB_URL" -c "SELECT COUNT(*) FROM chunk_embeddings;"
  psql "$PUBMEDFLO_DB_URL" -c "SELECT COUNT(*) FROM query_logs;"
  ```
* **Backend unit tests**
  ```bash
  python -m pytest tests/test_curator_routes.py
  ```
  These override FastAPI dependencies to verify the curator listing/deletion behavior, including permission checks.

---

## Results and Outputs
* `python3 pubmed_pipeline.py --log-level INFO` – Processes 20 PDFs into 430 chunks, embeds them, and writes the FAISS index.
* `python3 -m core.index_flat --query "best treatment for central diabetes insipidus" --k 5` – Logs the query, prints the top results, and records entries in `query_logs` + `retrieves`.
* `python3 -m core.index_flat --answer --query "What is diabetes insipidus?"` – Generates a natural-language answer with `[PMID #######]` citations.
