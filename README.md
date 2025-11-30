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
* [Verification](#verification)

---

## Overview
At a ***high-level***, this phase implements a **complete question & answering system**. Phase 3 built the vector pipeline (chunking, embeddings, FAISS) and Phase 4 takes it further with a FastAPI backend and admin, curator, and end-user routes. The backend includes authentication, role-based access, curator document ingestion, and an end-user `/query` endpoint that returns LLM answers with citations (if enabled). All the data is stored in PostgreSQL (documents, chunks, embeddings, users, query logs) so the server can persist data and restart without losing functionality.

### Frontend UI Overview
There is also a frontend component that uses React + TypeScript (Vite). It talks to the FastAPI backend via `VITE_API_BASE` and provides different dashboards and permissions based on the user's role (end_user, curator, admin).

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

* **backend/app.py** – Creates the FastAPI app, sets CORS, registers auth/admin/curator/query routers, and manages DB pool lifecycle.
* **backend/auth.py** – Provides Signup/login/me logic with hashing, JWT creation/verification, and role guards.
* **backend/admin.py** – Admin-only endpoints for listing and editing users.
* **backend/curator.py** – Handles single document uploads (CSV or manual form metadata), stores documents, and enables listing and deleting documents with chunk and embedding stats.
* **backend/query.py** – `POST /query` endpoint that returns `answer`, `citations`, and `retrieved_chunks` for authenticated users.
* **backend/query_service.py** – Calls the shared retriever to run FAISS search, generate answers, and format citations.
* **backend/repository.py** – Connection pool + repositories for users and documents (role assignment, document stats, secure deletion checks).
* **pipeline/core/** – Unchanged vector pipeline modules (chunking, embeddings, FAISS index, retriever, answer generator).
* **pipeline/utils/** – Metadata parsing/syncing helpers, database writers for chunks/documents.
* **pipeline/pubmed_pipeline.py** – Rebuilds the index offline by reusing the same ingestion steps used by the backend.
* **frontend (React + TS, Vite)** – Frontend application that adds UI to the FastAPI backend. 
     * Key pieces:
          * `src/AuthContext.tsx` – Authentication state, JWT handling, current user.
          * `src/App.tsx` – Router and ProtectedRoute wrappers; defines pages.
          * `src/pages/` – LoginPage, SignupPage, SearchPage, CuratorDashboardPage, AdminDashboardPage.
          * `src/components/` – Reusable UI (Navbar, ProtectedRoute, CuratorUploadForm, DocumentsTable, etc.).

---

## Supporting Files & Directories

* **Phase4.sql** – Final relational schema (users/roles, documents, chunks, embeddings, query logs, retrieves).
* **reset.sql** – SQL utility script that truncates all the pipeline tables to reset the database while preserving schema.
* **requirements.txt** – Includes FastAPI, Uvicorn, JWT/passlib, OpenAI, psycopg, sentence-transformers, FAISS.
* **.env.example** – Template for `PUBMEDFLO_DB_URL`, `PUBMEDFLO_SECRET`, `OPENAI_API_KEY`, etc.
* **artifacts/** – FAISS index + metadata generated by the pipeline.

---

## Dependencies & Setup

```bash
cd phase4
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
npm install
```

### Initialize the Database Schema

```bash
psql "$PUBMEDFLO_DB_URL" -f pipeline/Phase4.sql
```

### Environment Variables

```bash
cp .env.example .env
```
Then open `.env` and set your credentials 
(API key can be obtained through [OpenAI Platform](https://platform.openai.com/api-keys):
```bash
PUBMEDFLO_DB_URL="postgresql://postgres:postgres@localhost:5432/pubmedflo"
PUBMEDFLO_SECRET="dev-secret-change-me"
PUBMEDFLO_JWT_ALGORITHM="HS256"
PUBMEDFLO_TOKEN_TTL="60"
PUBMEDFLO_CORS_ORIGINS="http://localhost:3000"
OPENAI_API_KEY="sk-your-key"   # optional; required for answer generation
# Frontend: set VITE_API_BASE to your running backend
VITE_API_BASE="http://localhost:8000"
```

* **NOTE**: You will need to set up a payment method and add at least **$5 in credit** to your OpenAI account before the API key can be used for requests.

---

## Running the System
```bash
cd phase4
```

1. **Build or refresh the FAISS artifacts (optional, Phase 3 pipeline)**
   ```bash
   python3 -m pipeline.pubmed_pipeline --log-level INFO
   ```
2. **Start the FastAPI backend**
   ```bash
   uvicorn backend.app:app --reload
   ```
3. **Start the frontend (Vite dev server)**
   ```bash
   cd frontend
   npm run dev
   cd ..
   ```
   By default runs on http://localhost:5173. Ensure `VITE_API_BASE` points to your backend (e.g., `http://localhost:8000`).
   ```

---

## Phase 4 Scenario Walkthroughs
This section covers all the grading scenarios with commands exactly how I put it on the terminal. Replace emails/passwords/file paths with your own values and set `TOKEN` to the JWT returned from `/login`.

### 3.1 User Scenarios
1. A new user signs up and is successfully added to the system.
```bash
curl -X POST http://localhost:8000/signup \
     -H "Content-Type: application/json" \
     -d '{"name":"user","email":"user@example.com","password":"aPassword1!"}'
```
```json
// Output
{"access_token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI1Iiwicm9sZXMiOlsiZW5kX3VzZXIiXSwiZXhwIjoxNzY0NDc3Mzk3fQ.dR96PPabBtGCmMACL_qcN4cdFqXN3bXr4tTxLVm7oZ8","token_type":"bearer","user":{"user_id":5,"name":"user","email":"user@example.com","roles":["end_user"],"created_at":"2025-11-29T22:11:37.400278"}}
```

2. The newly registered user logs in using their credentials.
```bash
curl -X POST http://localhost:8000/login \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d 'username=user@example.com&password=aPassword1!'
```
```json
// Output
{"access_token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI1Iiwicm9sZXMiOlsiZW5kX3VzZXIiXSwiZXhwIjoxNzY0NDc3NDMzfQ.Hw9L2_7pAMqmRXpPDImV1DL3c5E6XTxn3l1bFoRLRAc","token_type":"bearer","user":{"user_id":5,"name":"user","email":"user@example.com","roles":["end_user"],"created_at":"2025-11-29T22:11:37.400278"}}
```

3. An admin logs in and retrieves a list of all registered users.
```bash
# Prerequisites (create admin and login) 
curl -X POST http://localhost:8000/signup \
     -H "Content-Type: application/json" \
     -d '{"name":"admin","email":"admin@example.com","password":"aPassword1!", "roles":["admin"]}'
curl -X POST http://localhost:8000/login \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d 'username=admin@example.com&password=aPassword1!'
```
```json
// Prerequisite Output 
{"access_token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI3Iiwicm9sZXMiOlsiYWRtaW4iXSwiZXhwIjoxNzY0NDc3OTQwfQ.hn6N1gtClTQ1DgD-3RwhBE2gzj679kTUbCERMCinkFQ","token_type":"bearer","user":{"user_id":7,"name":"admin","email":"admin@example.com","roles":["admin"],"created_at":"2025-11-29T22:20:40.389287"}}

{"access_token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI3Iiwicm9sZXMiOlsiYWRtaW4iXSwiZXhwIjoxNzY0NDc3OTQwfQ.hn6N1gtClTQ1DgD-3RwhBE2gzj679kTUbCERMCinkFQ","token_type":"bearer","user":{"user_id":7,"name":"admin","email":"admin@example.com","roles":["admin"],"created_at":"2025-11-29T22:20:40.389287"}}
```

```bash
curl -X GET "http://localhost:8000/admin/users" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI3Iiwicm9sZXMiOlsiYWRtaW4iXSwiZXhwIjoxNzY0NDc3OTQwfQ.hn6N1gtClTQ1DgD-3RwhBE2gzj679kTUbCERMCinkFQ"
```
```json
// Output
[{"user_id":5,"name":"user","email":"user@example.com","roles":["end_user"],"created_at":"2025-11-29T22:11:37.400278"},{"user_id":7,"name":"admin","email":"admin@example.com","roles":["admin"],"created_at":"2025-11-29T22:20:40.389287"}]
```

4. The admin edits the profile information of an existing user.
```bash
curl -X PUT "http://localhost:8000/admin/users/5" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI3Iiwicm9sZXMiOlsiYWRtaW4iXSwiZXhwIjoxNzY0NDc3OTQwfQ.hn6N1gtClTQ1DgD-3RwhBE2gzj679kTUbCERMCinkFQ" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Name",
    "email": "updated.email@example.com",
    "password": null,
    "roles": ["end_user"]
  }'
```
```json
// Output
{"user_id":5,"name":"Updated Name","email":"updated.email@example.com","roles":["end_user"],"created_at":"2025-11-29T22:11:37.400278"}
```

5. All user accounts are stored and retrieved from the SQL database.
```bash
psql "postgresql://localhost:5432/pubmedflo" -c "SELECT user_id, name, email FROM users ORDER BY user_id;"
psql "postgresql://localhost:5432/pubmedflo" -c "SELECT user_id FROM admins ORDER BY user_id;"
psql "postgresql://localhost:5432/pubmedflo" -c "SELECT user_id, last_activity FROM end_users ORDER BY user_id;"
```
```text
 user_id |     name     |           email           
---------+--------------+---------------------------
       5 | Updated Name | updated.email@example.com
       7 | admin        | admin@example.com
(2 rows)

 user_id 
---------
       7
(1 row)

 user_id | last_activity 
---------+---------------
       5 | 
(1 row)
```


### 3.2 Curator Scenarios
1. A curator uploads a new document to the system, and it becomes available for search.
```bash
# Prerequisites (create curator and login) 
curl -X POST http://localhost:8000/signup \
     -H "Content-Type: application/json" \
     -d '{"name":"curator","email":"curator@example.com","password":"aPassword1!", "roles":["curator"]}'
curl -X POST http://localhost:8000/login \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d 'username=curator@example.com&password=aPassword1!'
```
```json
// Prerequisite Output 
{"access_token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI4Iiwicm9sZXMiOlsiY3VyYXRvciJdLCJleHAiOjE3NjQ0Nzg0NzR9.IuibP5MSFwvgrrKmAnDPMbocxRMnb5lno8A7jowF8cI","token_type":"bearer","user":{"user_id":8,"name":"curator","email":"curator@example.com","roles":["curator"],"created_at":"2025-11-29T22:29:34.007091"}}

{"access_token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI4Iiwicm9sZXMiOlsiY3VyYXRvciJdLCJleHAiOjE3NjQ0Nzg0NzR9.IuibP5MSFwvgrrKmAnDPMbocxRMnb5lno8A7jowF8cI","token_type":"bearer","user":{"user_id":8,"name":"curator","email":"curator@example.com","roles":["curator"],"created_at":"2025-11-29T22:29:34.007091"}}
```

```bash
# CSV File
curl -X POST "http://localhost:8000/curator/upload" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI4Iiwicm9sZXMiOlsiY3VyYXRvciJdLCJleHAiOjE3NjQ0Nzg0NzR9.IuibP5MSFwvgrrKmAnDPMbocxRMnb5lno8A7jowF8cI" \
  -F "document=@/Users/nathan/Downloads/new-data/Anti-PD-1 Treatment-Induced Immediate Central Diabetes Insipidus  A Case Report.pdf" \
  -F "metadata_csv=@/Users/nathan/Downloads/new-data/new_csv.csv"


# Manual Metadata Entry
curl -X POST http://localhost:8000/curator/upload \
     -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI4Iiwicm9sZXMiOlsiY3VyYXRvciJdLCJleHAiOjE3NjQ0Nzg0NzR9.IuibP5MSFwvgrrKmAnDPMbocxRMnb5lno8A7jowF8cI" \
     -F "document=@/Users/nathan/Downloads/new-data/amjcaserep-22-e934193.pdf" \
     -F "pmid=34898594" \
     -F "title=Adipsic Diabetes Insipidus in Children: A Case Report and Practical Guide" \
     -F "authors=AlShoomi AM, Alkanhal KI, Alsaheel AY." \
     -F "doi=10.12659/AJCR.934193" \
     -F "journal_name=Am J Case Rep" \
     -F "publication_year=2021"

```

```json
// CSV File Output
{"message":"Document ingested successfully.","pmid":34424037,"doc_id":21,"title":"Anti-PD-1 treatment-induced immediate central diabetes insipidus: a case report","chunks":11,"embeddings":11,"metadata_source":"csv"}

// Manual Metadata Entry Output
{"message":"Document ingested successfully.","pmid":34898594,"doc_id":22,"title":"Adipsic Diabetes Insipidus in Children: A Case Report and Practical Guide","chunks":14,"embeddings":14,"metadata_source":"form"}
```

2. A curator removes one of their previously uploaded documents from the system.
```bash
curl -X DELETE "http://localhost:8000/curator/documents/22" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI4Iiwicm9sZXMiOlsiY3VyYXRvciJdLCJleHAiOjE3NjQ0NzkzMzJ9.Z5QPu4N9IykJDiZ64qdx-fLQWqcZdTbMHMi-SzHTqhk"
```
No output.

3. The system stores all document metadata correctly from the SQL database.
Ran before step 2:
```bash
psql "postgresql://localhost:5432/pubmedflo" -c "SELECT doc_id, title, pmid FROM documents WHERE doc_id = 21;"
psql "postgresql://localhost:5432/pubmedflo" -c "SELECT pmid, title, doi, publication_year FROM pubmed_articles WHERE pmid = 34424037;"
psql "postgresql://localhost:5432/pubmedflo" -c "SELECT doc_id, title, pmid FROM documents WHERE doc_id = 22;"
psql "postgresql://localhost:5432/pubmedflo" -c "SELECT pmid, title, doi, publication_year FROM pubmed_articles WHERE pmid = 34898594;"
```
```text
 doc_id |                                      title                                      |   pmid   
--------+---------------------------------------------------------------------------------+----------
     21 | Anti-PD-1 treatment-induced immediate central diabetes insipidus: a case report | 34424037
(1 row)

   pmid   |                                      title                                      |          doi          | publication_year 
----------+---------------------------------------------------------------------------------+-----------------------+------------------
 34424037 | Anti-PD-1 treatment-induced immediate central diabetes insipidus: a case report | 10.2217/imt-2020-0334 |             2021
(1 row)

 doc_id |                                   title                                   |   pmid   
--------+---------------------------------------------------------------------------+----------
     22 | Adipsic Diabetes Insipidus in Children: A Case Report and Practical Guide | 34898594
(1 row)

   pmid   |                                   title                                   |         doi          | publication_year 
----------+---------------------------------------------------------------------------+----------------------+------------------
 34898594 | Adipsic Diabetes Insipidus in Children: A Case Report and Practical Guide | 10.12659/ajcr.934193 |             2021
(1 row)

```

Ran after step 2:
```bash
psql "postgresql://localhost:5432/pubmedflo" -c "SELECT doc_id, title, pmid FROM documents WHERE doc_id = 21;"
psql "postgresql://localhost:5432/pubmedflo" -c "SELECT pmid, title, doi, publication_year FROM pubmed_articles WHERE pmid = 34424037;"
psql "postgresql://localhost:5432/pubmedflo" -c "SELECT doc_id, title, pmid FROM documents WHERE doc_id = 22;"
psql "postgresql://localhost:5432/pubmedflo" -c "SELECT pmid, title, doi, publication_year FROM pubmed_articles WHERE pmid = 34898594;"
```
```text
 doc_id |                                      title                                      |   pmid   
--------+---------------------------------------------------------------------------------+----------
     21 | Anti-PD-1 treatment-induced immediate central diabetes insipidus: a case report | 34424037
(1 row)

   pmid   |                                      title                                      |          doi          | publication_year 
----------+---------------------------------------------------------------------------------+-----------------------+------------------
 34424037 | Anti-PD-1 treatment-induced immediate central diabetes insipidus: a case report | 10.2217/imt-2020-0334 |             2021
(1 row)

 doc_id | title | pmid 
--------+-------+------
(0 rows)

 pmid | title | doi | publication_year 
------+-------+-----+------------------
(0 rows)
```

4. All documents and embeddings persist across system restarts and are automatically reloaded
into the vector database.
```bash
# Stop the server (Ctrl+C)
# then:
uvicorn backend.app:app --reload
psql "postgresql://localhost:5432/pubmedflo" -c "SELECT doc_id, title, pmid FROM documents WHERE doc_id = 21;"
```
Same output.


### 3.3 EndUser Scenarios
1. An end user submits a query to the system and receives a response.
```bash
# Prerequisites (login to end user) 
curl -X POST http://localhost:8000/login \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d 'username=updated.email@example.com&password=aPassword1!'
```
```json
// Prerequisite Output 
{"access_token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI1Iiwicm9sZXMiOlsiZW5kX3VzZXIiXSwiZXhwIjoxNzY0NDgwNjU3fQ.LfJudJUmYsN8PHTU7h25qtmHz2dIgukXm3X-klM-8zI","token_type":"bearer","user":{"user_id":5,"name":"Updated Name","email":"updated.email@example.com","roles":["end_user"],"created_at":"2025-11-29T22:11:37.400278"}}
```

```bash
curl -X POST "http://localhost:8000/query" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI1Iiwicm9sZXMiOlsiZW5kX3VzZXIiXSwiZXhwIjoxNzY0NDgwNjU3fQ.LfJudJUmYsN8PHTU7h25qtmHz2dIgukXm3X-klM-8zI" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "central diabetes insipidus treatment",
    "top_k": 3
  }'
```
```json
// Output
{"query_id":1,"answer":"The primary treatment for central diabetes insipidus (CDI) is desmopressin, a synthetic analog of vasopressin, which is used to alleviate symptoms such as polyuria, polydipsia, and nocturia. Desmopressin can be administered via several routes: intranasal, oral, subcutaneous, or intravenously. Intranasal administration is typically preferred due to variability in patient responses to oral forms [PMID 32741486]. \n\nFor intranasal desmopressin, the initial dose is generally 10-20 µg, given at bedtime and potentially titrated based on the patient's response. In cases where the oral route is used, the starting dose is usually 0.05 mg at bedtime, with possible titration upwards according to individual needs [PMID 33713498][PMID 36007536]. \n\nIt's essential to tailor the treatment based on individual responses and to monitor for potential side effects, such as water retention or hyponatremia [PMID 32741486][PMID 36007536]. For patients with CDI that occurs after neurosurgery, the condition may be transient, and desmopressin dosage can be adjusted based on the severity of symptoms [PMID 32741486].","citations":[{"pmid":32741486,"title":"Diabetes Insipidus: An Update","doc_id":5},{"pmid":38693275,"title":"Arginine vasopressin deficiency: diagnosis, management and the relevance of oxytocin deficiency","doc_id":20},{"pmid":33713498,"title":"Diagnosis and management of diabetes insipidus for the internist: an update","doc_id":13},{"pmid":36007536,"title":"Central diabetes insipidus from a patient's perspective: management, psychological co-morbidities, and renaming of the condition: results from an international web-based survey","doc_id":8},{"pmid":34522399,"title":"Management of Diabetes Insipidus following Surgery for Pituitary and Suprasellar Tumours","doc_id":14}],"retrieved_chunks":[{"chunk_id":86,"pmid":32741486,"doc_id":5,"title":"Diabetes Insipidus: An Update","score":0.6392565965652466,"chunk_text":"dosed empirically. The initial aim of therapy is to reduce nocturia and therefore the first dose is usually given at bedtime and, if needed, a daytime dose is added. In most cases, diabetes insipidus is permanent and therefore requires lifelong treatment. However, after neurosurgery, diabetes insipidus is mostly only tran-sient. 55Therefore, patients with diabetes insipidus after trans-sphenoidal surgery should not receive a fixed dose of desmopressin, but the degree of polyuria should be monitored and if polyuria becomes less pronounced or ceases, desmopressincan be tapered or withdrawn. If diabetes insipidus is still present 2 weeks after sur- gery, permanent diabetes insipidus becomes more likely. Desmopressin can be administered intranasally, orally, subcutaneously, or intravenously ( Table 2 ). Usually, starting with an intranasal preparation is recommended because not all pa- tients respond to oral therapy. For the intranasal preparation, an initial dose of 10 mga t bedtime can be titrated upward in 10 mg increments. The usual daily maintenance Table 2 Different forms and administrations of desmopressin treatment ApplicationIV/SC/ IM Intranasal Per Os Sublingual Concentration 4 mg/mL 0.1 mg/mL 10mg/dosage100/200 mg tablets 60/120/240 mg tablets Starting dosage 1 mg1 0 mg5 0 mg6 0 mgRefardt et al 526 Downloaded for Anonymous User (n/a) at University of Illinois Chicago from ClinicalKey.com by Elsevier on November 04, 2025. For personal use only. No other uses without permission. Copyright 2025. Elsevier Inc. All rights reserved. dose is 10 to 20 mg once or twice per day. For the oral preparation, the initial dose is 0.05 mg at bedtime with titration upward until 0.10 mg to 0.80 mg (maximum of 1.2 mg)in divided doses. Because the oral dose cannot be precisely predicted from a previous nasal dose, transfer of patients from nasal to oral therapy usually requires some dose retitration. For intravenous administration, 1 to 2 mg of desmopressin acetate may be given over 2 minutes; the duration of action is 12 hours or more. A special challenge in treatment are patients with osmoreceptor dysfunction. The long-term management of these patients requires measures to prevent dehydration and at the same time to prevent water intoxication. Because loss of thirst perception mostly cannot be cured, the focus of management is based on education of the pa-tient about the importance of regulating their fluid intake according to their hydrationstatus. 56This monitoring"},{"chunk_id":424,"pmid":38693275,"doc_id":20,"title":"Arginine vasopressin deficiency: diagnosis, management and the relevance of oxytocin deficiency","score":0.6787813305854797,"chunk_text":"series. Nephrol. Dial. Transplant. 29, 23102315 (2014). 56. Bichet, D. G. Regulation of thirst and vasopressin release. Annu. Rev. Physiol. 81, 359373 (2019). 57. Kim, G. H. Pathophysiology of drug-induced hyponatremia. J. Clin. Med. 11, 5810 (2022). 58. Tomkins, M., Lawless, S., Martin-Grace, J., Sherlock, M. & Thompson, C. J. Diagnosis and management of central diabetes insipidus in adults. J. Clin. Endocrinol. Metab. 107, 27012715 (2022). 59. Teare, H. et al. Challenges and improvement needs in the care of patients with central diabetes insipidus. Orphanet. J. Rare Dis. 17, 58 (2022). Nature Reviews Endocrinology | Volume 20 | August 2024 | 487500 499 Review article60. Christ-Crain, M., Winzeler, B. & Refardt, J. Diagnosis and management of diabetes insipidus for the internist: an update. J. Intern. Med. 290, 7387 (2021). 61. Melmed, S., Polonsky, K. S., Larsen, P. R. & Kronenberg, H. M. Williams Textbook of Endocrinology 14th edn (Elsevier, 2019). 62. Fukuda, I., Hizuka, N. & Takano, K. Oral DDAVP is a good alternative therapy for patients with central diabetes insipidus: experience of five-year treatment. Endocr. J. 50, 437443 (2003). 63. Kataoka, Y., Nishida, S., Hirakawa, A., Oiso, Y. & Arima, H. Comparison of incidence of hyponatremia between intranasal and oral desmopressin in patients with central diabetes insipidus. Endocr. J. 62, 195200 (2015). 64. Althammer, F. & Grinevich, V. Diversity of oxytocin neurons: beyond magno- and parvocellular cell types? J. Neuroendocrinol. https://doi.org/10.1111/jne.12549 (2017). 65. Althammer, F., Eliava, M. & Grinevich, V. Central and peripheral release of oxytocin: relevance of neuroendocrine and neurotransmitter actions for physiology and behavior. Handb. Clin. Neurol. 180, 2544 (2021). 66. Swanson, L. W. & Sawchenko, P. E. Hypothalamic integration: organization of the paraventricular and supraoptic nuclei. Annu. Rev. Neurosci. 6, 269324 (1983). 67. Zhang, B. et al. Reconstruction of the hypothalamo-neurohypophysial system and functional dissection of magnocellular oxytocin neurons in the brain. Neuron 109, 331346.e7 (2021). 68. Knobloch, H. S. et al. Evoked axonal oxytocin release in the central amygdala attenuates fear response. Neuron 73, 553566 (2012). 69. Mitre, M. et al. A distributed network for social cognition enriched for oxytocin receptors. J. Neurosci. 36, 25172535 (2016). 70. Oliveira, V. E. M. et al. Oxytocin and vasopressin within the ventral and dorsal lateral septum modulate aggression in female rats. Nat. Commun. 12, 2900 (2021). 71. Meyer-Lindenberg, A., Domes, G., Kirsch,"},{"chunk_id":234,"pmid":33713498,"doc_id":13,"title":"Diagnosis and management of diabetes insipidus for the internist: an update","score":0.6811990737915039,"chunk_text":"doi: 10.1111/joim.13261 Diagnosis and management of diabetes insipidus for the internist: an update M. Christ-Crain , B. Winzeler & J. Refardt From the Clinic for Endocrinology, Diabetes and Metabolism, University Hospital Basel, University of Basel, Basel, Switzerland Abstract. Christ-Crain M, Winzeler B, Refardt J (University Hospital Basel, University of Basel, Basel, Switzerland). Diagnosis and management of diabetes insipidus for the internist: an update(Review). J Intern Med 2021; 290:7 3 87. https:// doi.org/10.1111/joim.13261 Diabetes insipidus is a disorder characterized by excretion of large amounts of hypotonic urine. Four entities have to be differentiated: central diabetes insipidus resulting from a deciency of the hormonearginine vasopressin (AVP) in the pituitary gland or the hypothalamus, nephrogenic diabetes insipidus resulting from resistance to AVP in the kidneys,gestational diabetes insipidus resulting from an increase in placental vasopressinase and nally primary polydipsia, which involves excessive intakeof large amounts of water despite normal AVP secretion and action. Distinguishing between the different types of diabetes insipidus can bechallenging. A detailed medical history, physical examination and imaging studies are needed to detect the aetiology of diabetes insipidus. Differen- tiation between the various forms of hypotonicpolyuria is then done by the classical water depri- vation test or the more recently developed hypertonic saline or arginine stimulation together with copeptin(or AVP) measurement. In patients with idiopathiccentral DI, a close follow-up is needed since central DI can be the rst sign of an underlying pathology. Treatment of diabetes insipidus or primary polydip-sia depends on the underlying aetiology and differs in central diabetes insipidus, nephrogenic diabetes insipidus and primary polydipsia. This review willdiscuss issues and newest developments in diagno- sis, differential diagnosis and treatment, with a focus on central diabetes insipidus. Keywords: copeptin, diabetes insipidus, primary polydipsia, water deprivation test, diagnosis. Introduction Diabetes insipidus (DI) is a rare disease with a prevalence of ~1 in 25 000 individuals. The disor- der can manifest at any age, and the prevalence issimilar amongst males and females. Diabetes insipidus is a form of polyuria polydipsia syndrome and is characterized by excessive hypo-tonic polyuria ( >50 mL/kg body weight/24 h) and polydipsia ( >3 L/day) [1]. After exclusion of disor- ders of osmotic diuresis (such as uncontrolleddiabetes mellitus), the differential diagnosis of DI involves distinguishing between primary forms (central or renal) and secondary forms (resultingfrom primary polydipsia). A third, rare form of"},{"chunk_id":133,"pmid":36007536,"doc_id":8,"title":"Central diabetes insipidus from a patient's perspective: management, psychological co-morbidities, and renaming of the condition: results from an international web-based survey","score":0.6917861700057983,"chunk_text":"Science Foundation, Swiss Academy of Medical Sciences, and G&J Bangerter-Rhyner-Foundation. Copyright 2022 Elsevier Ltd. All rights reserved. Introduction Central diabetes insipidus, a rare neuroendocrine con dition with a prevalence of one in 25 000 people, is caused by arginine vasopressin deficiency.1 The condition is characterised by the production of large volumes of unconcentrated urine, which are compensated for by excessive fluid intake. 2 Once diagnosed, desmopressin, a selective vasopressin V2 receptor agonist, is usually prescribed to overcome the symptoms of polyuria, polydipsia, and nocturia. 3Data about desmopressin associated side effects, insuf cient awareness among medical professionals, and the prevalence of incorrect management of central diabetes insipidus are scarce and restricted to small studies or case series. Occasional published case reports show the tragic and fatal consequences of treatment neglect with omission of desmopressin during hospitalisation, which is partly explained by confusion among health care professionals between central diabetes insipidus and diabetes mellitus Downloaded for Anonymous User (n/a) at University of Illinois Chicago from ClinicalKey.com by Elsevier on November 05, 2025. For personal use only. No other uses without permission. Copyright 2025. Elsevier Inc. All rights reserved. Articleswww.thelancet.com/diabetes-endocrinology Vol 10 October 2022 701(diabetes).4 These examples of mismanagement and con fusion have given rise to increasing interest in the potential need for renaming central diabetes insipidus to avoid confusion with diabetes. An enormous amount of research has been devoted to quality of life (QoL) in patients with anterior pituitary dysfunction; however, research covering QoL and psycho logical comorbidities in patients with central diabetes insipidus is scarce. A few small studies have shown that even if patients were asymptomatic in terms of polyuria and polydipsia, psychological comorbidities occur, with adverse effects on QoL, compared with indi viduals with out diabetes insipidus.5,6 However, impor tant ques tions regard ing psychopathological char ac teristics remain unanswered. To address these issues, we aimed to assess patients perspectives regarding their disease management, psychological comorbidities, knowledge and awareness of the disease among health care professionals, and renaming central diabetes insipidus.of Metabolism and Systems Research, University of Birmingham, Birmingham, UK (N Karavitaki PhD); Centre for Endocrinology, Diabetes and Metabolism, Birmingham Health Partners, Birmingham, UK (N Karavitaki); University Hospitals Birmingham, NHS Foundation Trust, Birmingham, UK (N Karavitaki); Georgetown University Medical Center, Washington DC, USA (Prof J G Verbalis MD); Research Center for Clinical Neuroimmunology"},{"chunk_id":291,"pmid":34522399,"doc_id":14,"title":"Management of Diabetes Insipidus following Surgery for Pituitary and Suprasellar Tumours","score":0.7037122249603271,"chunk_text":"Kerrigan J, Clarke WL, Rogol AD, Blizzard RM. Treatment of the young child with postoperative central diabetes insipidus. Am J Dis Child 1989; 143:2014. https://doi.org/10.1001/archpedi.1989.02150140095027. 89. Gutmark-Little I, Repaske DR, Backeljauw PF. Efficacy and safety of intranasal desmopressin acetate administered orally for the management of infants with neurogenic diabetes insipidus (DI). Endocrine Rev 2010; 31:P3324. Management of Diabetes Insipidus following Surgery for Pituitary and Suprasellar Tumours364 | SQU Medical Journal, August 2021, Volume 21, Issue 390. Blanco EJ, Lane AH, Aijaz N, Blumberg D, Wilson TA. Use of subcutaneous DDAVP in infants with central diabetes insipidus. J Pediatr Endocrinol Metab 2006; 19:91925. https://doi.org/1 0.1515/jpem.2006.19.7.919. 91. Durr JA, Hoggard JG, Hunt JM, Schrier RW. Diabetes insipidus in pregnancy associated with abnormally high circulating vasopressinase activity. N Engl J Med 1987; 316:10704. https://doi.org/10.1056/NEJM198704233161707. 92. Barron WM. Water metabolism and vasopressin secretion during pregnancy. Baillieres Clin Obstet Gynaecol 1987; 1:85371. https://doi.org/10.1016/s0950-3552(87)80038-x . 93. Burrow GN, Wassenaar W, Robertson GL, Sehl H. DDAVP treatment of diabetes insipidus during pregnancy and the postpartumm period. Acta Endocrinol (Copenh) 1981; 97:235. https://doi.org/10.1530/acta.0.0970023. 94. Czernichow P . Treatment of diabetes insipidus. In: Argente J, Ed. Diabetes Insipidus. Madrid, Spain: Editorial Justim, 2010. Pp. 107112.95. Cuesta M, Hannon MJ, Thompson CJ. Adipsic diabetes insipidus in adult patients. Pituitary 2017; 20:37280. https:// doi.org/10.1007/s11102-016-0784-4. 96. Miljic D, Miljic P , Doknic M, Pekic S, Stojanovic M, Petakov M, et al. Adipsic diabetes insipidus and venous thromboembolism (VTE): Recommendations for addressing its hypercoagulability. Hormones (Athens) 2014; 13:4203. https://doi.org/10.14310/ horm.2002.1496. 97. Green RP , Landt M. Home sodium monitoring in patients with diabetes insipidus. J Pediatr 2002; 141:61824. https://doi. org/10.1067/mpd.2002.128544. 98. Ball SG, Vaidja B, Baylis PH. Hypothalamic adipsic syndrome: Diagnosis and management. Clin endocrinol (Oxf) 1997; 47:4059. https://doi.org/10.1046/j.1365-2265.1997.2591079.x . 99. Crowley RK, Woods C, Fleming M, Rogers B, Behan LA, O'Sullivan EP , et al. Somnolence in adult craniopharyngioma patients is a common, heterogeneous condition that is potentially treatable. Clin Endocrinol (Oxf) 2011; 74:7505. https://doi.org/10.1111/j.1365-2265.2011.03993.x ."}]}
```

2. A curator uploads a new document, and the end user successfully queries information related
to this newly added document.
```bash
# Prerequisites (login to curator) 
curl -X POST http://localhost:8000/login \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d 'username=curator@example.com&password=aPassword1!'
```
```json
// Prerequisite Output 
{"access_token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI4Iiwicm9sZXMiOlsiY3VyYXRvciJdLCJleHAiOjE3NjQ0ODA5MDR9.yYN-MLrnT8P1yJofaqVXnYl7tCAz6G9VgxRSUShuPRg","token_type":"bearer","user":{"user_id":8,"name":"curator","email":"curator@example.com","roles":["curator"],"created_at":"2025-11-29T22:29:34.007091"}}
```

```bash
curl -X POST http://localhost:8000/curator/upload \
     -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI4Iiwicm9sZXMiOlsiY3VyYXRvciJdLCJleHAiOjE3NjQ0ODA5MDR9.yYN-MLrnT8P1yJofaqVXnYl7tCAz6G9VgxRSUShuPRg" \
     -F "document=@/Users/nathan/Downloads/new-data/amjcaserep-22-e934193.pdf" \
     -F "pmid=34898594" \
     -F "title=Adipsic Diabetes Insipidus in Children: A Case Report and Practical Guide" \
     -F "authors=AlShoomi AM, Alkanhal KI, Alsaheel AY." \
     -F "doi=10.12659/AJCR.934193" \
     -F "journal_name=Am J Case Rep" \
     -F "publication_year=2021"

curl -X POST "http://localhost:8000/query" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI1Iiwicm9sZXMiOlsiZW5kX3VzZXIiXSwiZXhwIjoxNzY0NDgwNjU3fQ.LfJudJUmYsN8PHTU7h25qtmHz2dIgukXm3X-klM-8zI" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "management of adipsic diabetes insipidus in children",
    "top_k": 3
  }'
```
```json
// Output
{"message":"Document ingested successfully.","pmid":34898594,"doc_id":23,"title":"Adipsic Diabetes Insipidus in Children: A Case Report and Practical Guide","chunks":14,"embeddings":14,"metadata_source":"form"}

{"query_id":2,"answer":"The management of adipsic diabetes insipidus (DI) in children includes several key strategies. According to a case report, the main components of effective management involve:\n\n1. **Desmopressin Usage**: A fixed dosing schedule of desmopressin should be implemented to minimize urinary breakthroughs between doses.\n2. **Fluid Replacement**: Timely weight-based water replacement is crucial. This means monitoring the child's weight regularly to adjust fluid intake accordingly.\n3. **Scheduled Fluid Correction**: Bodyweight-based fluid correction should be done twice a day to ensure proper hydration.\n4. **Nutritional and Water Requirements**: It is important to provide the child with water and nutritional needs similar to those of a healthy child, but at fixed intervals to better manage their hydration status [PMID 34898594].\n\nOverall, adherence to this management plan can effectively control plasma sodium levels and ensure the child's overall well-being without hindering growth [PMID 34898594].","citations":[{"pmid":34898594,"title":"Adipsic Diabetes Insipidus in Children: A Case Report and Practical Guide","doc_id":30},{"pmid":27156767,"title":"Diabetes insipidus in infants and children","doc_id":6}],"retrieved_chunks":[{"chunk_id":539,"pmid":34898594,"doc_id":30,"title":"Adipsic Diabetes Insipidus in Children: A Case Report and Practical Guide","score":0.5610040426254272,"chunk_text":"Received: 2021.07.27 Accepted: 2021.10.26 Available online: 2021.11.05 Published: 2021.12.13 2495 2 18Adipsic Diabetes Insipidus in Children: A Case Report and Practical Guide ABCDEF Anas M. AlShoomi EF Khalid I. Alkanhal F Abdulhameed Y. Alsaheel Corresponding Author: Anas M. AlShoomi, e-mail: amalshoomi@yahoo.com Financial support: This study was funded by King Fahad Medical City, Riyadh, Saudi Arabia Conflict of interest: None declared Patient: Male, 2-year-old Final Diagnosis: Adipsic diabetes insipidus Symptoms: Dehydration polyuria Medication: Desmopressin Clinical Procedure: Fluid replacement Specialty: Pediatrics and Neonatology Endocrine and Metabolic Objective: Rare coexistence of disease or pathology Background: Diabetes insipidus (DI) is a clinical syndrome characterized by polyuria and polydipsia that result from a de - ficiency of antidiuretic hormone (ADH), central DI, or resistance to ADH, nephrogenic DI. In otherwise healthy patients with DI, normal thirst mechanism, and free access to water, the thirst system can maintain plasma osmolality in the near-normal range. However, in cases where DI presents with adipsia, cognitive impairment, or restricted access to water, true hypernatremia may occur, leading to severe morbidity and mortality. Case Report: We report a case of a 2-year-old boy who had global developmental delay and post-brain debulking surgery involving the hypothalamic region, which resulted in central DI and thirst center dysfunction. We describe the clinical presentation, the current understanding of adipsic DI, and a new practical approach for management. The main guidelines of treatment include (1) fixed desmopressin dosing that allows minimal urinary break - throughs in-between the doses; (2) timely diaper weight-based replacement of water; (3) bodyweight-based fluid correction 2 times a day, and (4) providing the nutritional and water requirements in a way similar to any healthy child but at fixed time intervals. Conclusions: This plan of management showed good effectiveness in controlling plasma sodium level and volume status of a child with adipsic DI without interfering with his average growth. This home treatment method is practical and readily available, provided that the family remains very adherent. Keywords: Adipsia Diabetes Insipidus Thirst Water-Electrolyte Balance Full-text PDF: https://www.amjcaserep.com/abstract/index/idArt/934193Authors Contribution: Study Design A Data Collection B Statistical Analysis C Data Interpretation D Manuscript Preparation E Literature Search F Funds Collection GDepartment of Pediatric Endocrinology, King Fahad Medical City, Riyadh, Saudi Arabiae-ISSN 1941-5923 Am J Case Rep, 2021; 22: e934193 DOI: 10.12659/AJCR.934193 e934193-1 Indexed in: [PMC] [PubMed] [Emerging Sources Citation Index"},{"chunk_id":112,"pmid":27156767,"doc_id":6,"title":"Diabetes insipidus in infants and children","score":0.6061174869537354,"chunk_text":"Post EM, Notman DD, et al. Simplifying the diagnosis of diabetes insipidus in children. Am J Dis Child 1981; 135(9):839 e41. *[16] Rivkees SA, Dunbar N, Wilson TA. The management of central diabetes insipidus in infancy: desmopressin, low renal solute load formula, thiazide diuretics. J Pediatr Endocrinol Metab 2007;20(4):459 e69. [17] Srivatsa AM, Joseph. Pediatric endocrinology. 2 ed. CRC Press; 2006 . [18] Karthikeyan A, Abid N, Sundaram PC, et al. Clinical characteristics and management of cranial diabetes insipidus in in- fants. J Pediatr Endocrinol Metab 2013;26(11 e12):1041 e6. [19] Robson WL, Leung AK, Norgaard JP. The comparative safety of oral versus intranasal desmopressin for the treatment of children with nocturnal enuresis. J Urol 2007;178(1):24 e30. *[20] Lofng J. Paradoxical antidiuretic effect of thiazides in diabetes insipidus: another piece in the puzzle. J Am Soc Nephrol 2004;15(11):2948 e50. [21] Abraham MB, Rao S, Price G, et al. Ef cacy of hydrochlorothiazide and low renal solute feed in neonatal central diabetes insipidus with transition to oral desmopressin in early infancy. Int J Pediatr Endocrinol 2014;2014(1):11 . *[22] Al Nofal A, Lteif A. Thiazide diuretics in the management of young children with central diabetes insipidus. J Pediatr 2015; 167(3):658 e61. [23] Alon U, Chan JC. Hydrochlorothiazide-amiloride in the treatment of congenital nephrogenic diabetes insipidus. Am J Nephrol 1985;5(1):9 e13. [24] Kirchlechner V, Koller DY, Seidl R, et al. Treatment of nephrogenic diabetes insipidus with hydrochlorothiazide and amiloride. Arch Dis Child 1999;80(6):548 e52. [25] De Waele K, Cools M, De Guchtenaere A, et al. Desmopressin lyophilisate for the treatment of central diabetes insipidus: rst experience in very young infants. Int J Endocrinol Metab 2014;12(4):e16120 . [26] Korkmaz HA, Demir K, Kilic FK, et al. Management of central diabetes insipidus with oral desmopressin lyophilisate in infants. J Pediatr Endocrinol Metab 2014;27(9 e10):923 e7. [27] Blanco EJ, Lane AH, Aijaz N, et al. Use of subcutaneous DDAVP in infants with central diabetes insipidus. J Pediatr Endocrinol Metab 2006;19(7):919 e25. *[28] Ghirardello S, Hopper N, Albanese A, et al. Diabetes insipidus in craniopharyngioma: postoperative management of water and electrolyte disorders. J Pediatr Endocrinol Metab 2006;19(Suppl. 1):413 e21. [29] Ball SG, Vaidja B, Baylis PH. Hypothalamic adipsic syndrome: diagnosis and management. Clin Endocrinol (Oxf) 1997; 47(4):405 e9. *[30] Di Iorgi N, Morana G, Napoli F, et al. Management of diabetes insipidus"},{"chunk_id":94,"pmid":27156767,"doc_id":6,"title":"Diabetes insipidus in infants and children","score":0.6273437738418579,"chunk_text":"12 Diabetes insipidus in infants and children Elizabeth Dabrowski, MD, Pediatric Endocrinology Fellows*, Rachel Kadakia, MD, Pediatric Endocrinology Fellows, Donald Zimmerman, MD, Head of the Division of Endocrinology at Ann and Robert H. Lurie Children's Hospital of Chicago Division of Endocrinology, Ann and Robert H. Lurie Children's Hospital of Chicago, Northwestern University Feinberg School of Medicine, 225 East Chicago Avenue, Box 54, Chicago, IL 60611, USA article info Article history: Available online 27 February 2016 Keywords: diabetes insipidusvasopressinpolyuriapolydipsia nephrogenic diabetes insipidusDiabetes insipidus, the inability to concentrate urine resulting in polyuria and polydipsia, can have different manifestations and management considerations in infants and children compared toadults. Central diabetes insipidus, secondary to lack of vasopressin production, is more common in children than is nephrogenic dia- betes insipidus, the inability to respond appropriately to vasopressin.The goal of treatment in both forms of diabetes insipidus is todecrease urine output and thirst while allowing for appropriate uid balance, normonatremia and ensuring an acceptable qualityof life for each patient. An infant's obligate need to consume calories as liquidand the need for readjustment of medication dosing in growing children both present unique challenges for diabetes insipidus management in the pediatric population. Treatment modalitiestypically include vasopressin or thiazide diuretics. Special consider- ation must be given when managing diabetes insipidus in the adipsic patient, post-surgical patient, and in those undergoing chemo-therapy or receiving medications that alter free water clearance. 2016 Elsevier Ltd. All rights reserved. Epidemiology Diabetes Insipidus (DI) is characterized by the inability to concentrate urine secondary to vaso- pressin de ciency or to vasopressin resistance resulting in polyuria. DI is rare, with a prevalence *Corresponding author. Tel.: 1 312 227 6090; Fax: 1 312 227 9403. E-mail addresses: Edabrowski@luriechildrens.org (E. Dabrowski), Rkadakia@luriechildrens.org (R. Kadakia), Dzimmerman@ luriechildrens.org (D. Zimmerman). Contents lists available at ScienceDirect Best Practice & Research Clinical Endocrinology & Metabolism journal homepage: www.elsevier.com/locate/beem http://dx.doi.org/10.1016/j.beem.2016.02.006 1521-690X/ 2016 Elsevier Ltd. All rights reserved.Best Practice & Research Clinical Endocrinology & Metabolism 30 (2016) 317 e328 estimated at 1:25,000; fewer than 10% of cases are hereditary in nature [1]. Central DI (CDI) accounts for greater than 90% of cases of DI and can present at any age, depending on the cause. No prevalence for hereditary causes of CDI has been established. Nephrogenic DI (NDI) is less frequent than CDI. X- linked NDI (XLNDI) accounts"},{"chunk_id":552,"pmid":34898594,"doc_id":30,"title":"Adipsic Diabetes Insipidus in Children: A Case Report and Practical Guide","score":0.6596775650978088,"chunk_text":"in healthy man. Clin Sci (Lond). 1986;71(6):651-56 16. Freige C, Spry C. Oral rehydration solutions versus drink of choice in chil - dren with dehydration: A review of clinical effectiveness [Internet]. Ottawa (ON): Canadian Agency for Drugs and Technologies in Health; 2020 Mar 2. PMID: 33074626 17. Hameed S, Mendoza-Cruz AC, Neville KA, et al. Home blood sodium moni - toring, sliding-scale fluid prescription and subcutaneous DDAVP for infantile diabetes insipidus with impaired thirst mechanism. Int J Pediatr Endocrinol 2012;2012(1):18 18. Pabich S, Flynn M, Pelley E. Daily sodium monitoring and fluid intake pro - tocol: Preventing recurrent hospitalization in adipsic diabetes insipidus. J Endocr Soc. 2019;3(5):882-86 AlShoomi A.M. et al: Adipsic diabetes insipidus in children Am J Case Rep, 2021; 22: e934193 e934193-6 Indexed in: [PMC] [PubMed] [Emerging Sources Citation Index (ESCI)] [Web of Science by Clarivate]This work is licensed under Creative Common Attribution- NonCommercial-NoDerivatives 4.0 International (CC BY-NC-ND 4.0)"},{"chunk_id":113,"pmid":27156767,"doc_id":6,"title":"Diabetes insipidus in infants and children","score":0.6997093558311462,"chunk_text":"S, Hopper N, Albanese A, et al. Diabetes insipidus in craniopharyngioma: postoperative management of water and electrolyte disorders. J Pediatr Endocrinol Metab 2006;19(Suppl. 1):413 e21. [29] Ball SG, Vaidja B, Baylis PH. Hypothalamic adipsic syndrome: diagnosis and management. Clin Endocrinol (Oxf) 1997; 47(4):405 e9. *[30] Di Iorgi N, Morana G, Napoli F, et al. Management of diabetes insipidus and adipsia in the child. Best Pract Res Clin Endocrinol Metab 2015;29(3):415 e36. [31] Woodmansee WW, Carmichael J, Kelly D, et al. American association of clinical endocrinologists and American college of endocrinology disease state clinical review: postoperative management following pituitary surgery. Endocr Pract 2015; 21(7):832 e8. [32] Mukherjee KK, Dutta P, Singh A, et al. Choice of uid therapy in patients of craniopharyngioma in the perioperative period: a hospital-based preliminary study. Surg Neurol Int 2014;5:105 . [33] Bouley R, Hasler U, Lu HA, et al. Bypassing vasopressin receptor signaling pathways in nephrogenic diabetes insipidus. Semin Nephrol 2008;28(3):266 e78. [34] Moeller HB, Rittig S, Fenton RA. Nephrogenic diabetes insipidus: essential insights into the molecular background and potential therapies for treatment. Endocr Rev 2013;34(2):278 e301. [35] Procino G, Barbieri C, Carmosino M, et al. Fluvastatin modulates renal water reabsorption in vivo through increased AQP2 availability at the apical plasma membrane of collecting duct cells. P ugers Arch 2011;462(5):753 e66. [36] Bonfrate L, Procino G, Wang DQ, et al. A novel therapeutic effect of statins on nephrogenic diabetes insipidus. J Cell Mol Med 2015;19(2):265 e82.E. Dabrowski et al. / Best Practice & Research Clinical Endocrinology & Metabolism 30 (2016) 317 e328 327 [37] Assadi F, Ghane Sharbaf F. Sildena l for the treatment of congenital nephrogenic diabetes insipidus. Am J Nephrol 2015; 42(1):65 e9. [38] Bryant WP, O0Marcaigh AS, Ledger GA, et al. Aqueous vasopressin infusion during chemotherapy in patients with diabetes insipidus. Cancer 1994;74(9):2589 e92. [39] Alsady M, Baumgarten R, Deen PM, et al. Lithium in the kidney: friend and foe? J Am Soc Nephrol 2015 [Epub ahead of print] . [40] Marples D, Christensen S, Christensen EI, et al. Lithium-induced downregulation of aquaporin-2 water channel expression in rat kidney medulla. J Clin Invest 1995;95(4):1838 e45. [41] Christensen BM, Marples D, Kim YH, et al. Changes in cellular composition of kidney collecting duct cells in rats with lithium-induced NDI. Am J Physiol Cell Physiol 2004;286(4):C952 e64.E. Dabrowski et"}]}

```

3. All query logs are properly stored and retrievable from the SQL database.
```bash
psql "postgresql://localhost:5432/pubmedflo" -c "SELECT row_to_json(q)
FROM (
  SELECT query_id, query_text, response_text, issued_at, user_id
  FROM query_logs
) AS q;"
```
Needed to convert output to JSON for better readability.
```json
{"query_id":1,"query_text":"central diabetes insipidus treatment","response_text":"The primary treatment for central diabetes insipidus (CDI) is desmopressin, a synthetic analog of vasopressin, which is used to alleviate symptoms such as polyuria, polydipsia, and nocturia. Desmopressin can be administered via several routes: intranasal, oral, subcutaneous, or intravenously. Intranasal administration is typically preferred due to variability in patient responses to oral forms [PMID 32741486]. \n\nFor intranasal desmopressin, the initial dose is generally 10-20 µg, given at bedtime and potentially titrated based on the patient's response. In cases where the oral route is used, the starting dose is usually 0.05 mg at bedtime, with possible titration upwards according to individual needs [PMID 33713498][PMID 36007536]. \n\nIt's essential to tailor the treatment based on individual responses and to monitor for potential side effects, such as water retention or hyponatremia [PMID 32741486][PMID 36007536]. For patients with CDI that occurs after neurosurgery, the condition may be transient, and desmopressin dosage can be adjusted based on the severity of symptoms [PMID 32741486].","issued_at":"2025-11-29T23:06:22.154773","user_id":5}

{"query_id":2,"query_text":"management of adipsic diabetes insipidus in children","response_text":"The management of adipsic diabetes insipidus (DI) in children includes several key strategies. According to a case report, the main components of effective management involve:\n\n1. **Desmopressin Usage**: A fixed dosing schedule of desmopressin should be implemented to minimize urinary breakthroughs between doses.\n2. **Fluid Replacement**: Timely weight-based water replacement is crucial. This means monitoring the child's weight regularly to adjust fluid intake accordingly.\n3. **Scheduled Fluid Correction**: Bodyweight-based fluid correction should be done twice a day to ensure proper hydration.\n4. **Nutritional and Water Requirements**: It is important to provide the child with water and nutritional needs similar to those of a healthy child, but at fixed intervals to better manage their hydration status [PMID 34898594].\n\nOverall, adherence to this management plan can effectively control plasma sodium levels and ensure the child's overall well-being without hindering growth [PMID 34898594].","issued_at":"2025-11-29T23:12:07.895894","user_id":5}
(2 rows)
```

4. An admin deletes an end user, and all associated data (e.g., query logs) is correctly removed
from the system.
```bash
# Prerequisites (login to admin) 
curl -X POST http://localhost:8000/login \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d 'username=admin@example.com&password=aPassword1!'
```
```json
// Prerequisite Output 
{"access_token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI3Iiwicm9sZXMiOlsiYWRtaW4iXSwiZXhwIjoxNzY0NDgxODQ3fQ.9PLb_G4-ctbuD7C-yY_H-MPgLY9bvgKQq_nbfaun1os","token_type":"bearer","user":{"user_id":7,"name":"admin","email":"admin@example.com","roles":["admin"],"created_at":"2025-11-29T22:20:40.389287"}}
```

Before deleting:
```bash
psql "postgresql://localhost:5432/pubmedflo" -c "SELECT COUNT(*) FROM query_logs;"
```
```text
 count 
-------
     2
(1 row)
```

Delete user:
```bash
curl -X DELETE "http://localhost:8000/admin/users/5" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI3Iiwicm9sZXMiOlsiYWRtaW4iXSwiZXhwIjoxNzY0NDgxODQ3fQ.9PLb_G4-ctbuD7C-yY_H-MPgLY9bvgKQq_nbfaun1os"
```
No output.

After deleting:
```bash
psql "postgresql://localhost:5432/pubmedflo" -c "SELECT COUNT(*) FROM query_logs;"
```
```text
 count 
-------
     0
(1 row)
```

### 3.4 Bonus
`cd frontend` then run `npm run dev` and go through **3.1-3.3 scenarios**.

---

## Example Queries
Here are some other examples you can try after building the FAISS index:
* How to diagnose central diabetes insipidus
* Key complications reported by patients living with diabetes insipidus
* causes of diabetes insipidus
* symptoms of central diabetes insipidus
* What is diabetes insipidus and how is it different from diabetes?
* What fluid management strategies are recommended for DI?
* What is the first-line treatment for central diabetes insipidus?
* How does desmopressin work to treat diabetes insipidus?

Query that is partially relevant to the corpus but not directly covered:
* risk factors for developing diabetes
    * *Note*: This example highlights a downside of using L2 distance in FAISS. The scores (~0.9–1.1) appear “close,” but L2 distances on unnormalized MiniLM embeddings are hard to interpret. Even irrelevant matches may show similar distances, unlike cosine similarity where the relevance threshold is clearer (~0.42-0.5). L2 and cosine ranges are discussed in the [Project Description](#project-description) section.

Example of some queries that will **not** return an answer:
* best treatment for type 2 diabetes
* preventing progression of diabetes
* Founding of the US

Queries specific to **new uploaded documents** (Phase 4):
* 
* 
* 

Use `--answer` to see GPT‑4o-mini synthesize responses with inline `[PMID ######]` citations taken from the retrieved snippets.

---

## Verification

* **Database sanity checks**
  ```bash
  psql "$PUBMEDFLO_DB_URL" -c "SELECT COUNT(*) FROM users;"
  psql "$PUBMEDFLO_DB_URL" -c "SELECT COUNT(*) FROM documents;"
  psql "$PUBMEDFLO_DB_URL" -c "SELECT COUNT(*) FROM chunk_embeddings;"
  psql "$PUBMEDFLO_DB_URL" -c "SELECT COUNT(*) FROM query_logs;"
  ```