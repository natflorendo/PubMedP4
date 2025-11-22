# CS 480 - Phase 3: PubMedFlo Vector Retrieval Pipeline

**Name:** Nathan Florendo

---

## Table of Contents

* [Overview](#overview)
* [Project Description](#project-description)
* [Pipeline Architecture](#pipeline-architecture)
* [Source Files Summary](#source-files-summary)
* [Supporting Files & Directories](#supporting-files--directories)
* [Dependencies & Setup](#dependencies--setup)
* [Running the Pipeline](#running-the-pipeline)
* [Example Queries](#example-queries)
* [Verification and Database Checks](#verification-and-database-checks)
* [Results and Outputs](#results-and-outputs)

---

## Overview
At a ***high-level***, this project implements a **vector-based retrieval pipeline** for the *PubMed* system, focusing on diabetes treatment.

The pipeline extracts, chunks, and embeds text from a folder containing PDFs (or text files), parses associated metadata, then stores all the vectors in PostgreSQL. It then builds a FAISS index for nearest-neighbor search.

There is also an option to use an LLM that uses the top-k retrieved chunks to generate an answer with inline citations.

All the sections included in this `README` are things I found useful to understand the project structure faster and make setup easier.

---

## Project Description
This section gives a ***step-by-step*** breakdown of the main workflow. It summarizes how the system transforms raw PubMed PDFs into an indexed, queryable vector database with optional LLM synthesis (produces an answer that uses the relevant facts from retrieved chunks).

* **Parse & Chunk**: Reads raw PubMed PDFs, extracts normalized text, and splits it into deterministic overlapping chunks.
* **Embed**: Converts each chunk into a vector representation using the `sentence-transformers/all-MiniLM-L6-v2` model.
* **Index & Query**: Builds a FAISS similarity index (`IndexFlatL2` or `IndexFlatIP`) and retrieves the top-k most relevant chunks for a given query.
    * Interpret FAISS scores based on the metric used:
        * For L2 (IndexFlatL2): lower distance = higher similarity. **Range is from 0 to ∞**.
        * For cosine/inner product (IndexFlatIP): higher score = higher similarity. **Range is from -1 to 1**.
* **LLM Answer Generation (optional)**: Produces a concise natural-language answer with the top-k retrieved chunks, with inline `[PMID ########]` citations.
* **Logging**: Records each query (and optionally the generated answer) in `query_logs`, and stores the documents the chunks are retrieved from in the `retrieves` table.

---

## Pipeline Architecture
This shows how each stage of the retrieval pipeline maps directly onto the codebase, providing a ***code-level view*** of how the system is implemented end to end.

PDF -> Extract -> Chunk -> Embed -> FAISS Index -> Query -> Top-k Chunks -> LLM Answer

### How the Stages Are Split Across the Codebase
* `pubmed_pipeline.py` handles the entire offline build pipeline:
    * PDF -> Extract (via `core/pdf_reader.py`)
    * Extract -> Chunk (via `core/chunker.py`)
        * PDF -> Chunk (via `core/parse_directory.py`)
    * Chunk -> Embed (via `core/embed_chunks.py`)
    * Embed -> FAISS Index (via `core/index_builder.py`, triggered internally through the `run()` function in `core/index_flat.py`)
* **NOTE**: `pubmed_pipeline.py` calls `parse_directory.run()`, then `embed_chunks.run()`, then `index_flat.run()`
* `core/index_flat.py` is used separately for online querying and answer generation:
    * `--query "<text>"` runs the vector search step (FAISS Index -> Top-k Chunks)
    * `--k <int>` controls the number of chunks returned (default = 5)
    * `--answer` triggers the LLM Answer step (Top-k Chunks -> LLM Answer)
* The [Source Files Summary](#source-files-summary) section below breaks down the purpose of each file referenced here.

---

## Source Files Summary
This section lists out each file and gives a short summary of the purpose they serve.

* **pubmed_pipeline.py** - Main orchestrator that loads PDFs, chunks the text, generates embeddings, and builds a FAISS index.

### config/
* **config.toml** - Defines all runtime settings such as the database URL, input paths, chunk size, embedding model, and LLM model for answer generation.
* **config.py** - Loads configuration sections and defines dataclasses for each one.

### utils/
* **metadata_parser.py** - Parses raw PubMed CSV exports into structured, immutable objects.
* **metadata_sync.py** - Synchronizes parsed PubMed metadata with PostgreSQL by performing journal, author, and article upserts.
* **metadata_lookup.py** - Resolves document metadata by matching DOIs or titles against document text.
* **metadata_loader.py** - Central file that re-exports metadata parsing, synchronization, and lookup utilities for unified external access.
* **db_writer.py** - Ensures documents exist, updates changed fields, upserts text chunks, and removes stale chunks for each PubMed article.

### core/
* **pdf_reader.py** - Does PDF parsing via PyPDF2 and normalizes the text for chunking.
* **chunker.py** - Normalizes further (drop non-ASCII characters) and splits extracted text into overlapping chunks with hashes and offsets.
* **parse_directory.py** - Loads CSV metadata and syncs the articles, journals, authors, and chunks to the database.
* **embed_chunks.py** - Generates embeddings from chunks, and stores them in the database.
* **index_builder.py** - Builds and maintains the FAISS index from stored embeddings and writes artifacts (`.faiss`, `.ids.npy`, `.meta.json`).
* **answer_generator.py** - Uses OpenAI’s ChatCompletion API to produce natural language, cited answers.
* **retriever.py** - Runs FAISS search, fetches metadata, logs queries, and stores generated answers.
* **index_flat.py** - Orchestrates building and retrieving the FAISS index, supports cosine/L2 metrics, CLI for querying, and integrates the configured LLM model for answer generation.

---

## Supporting Files & Directories
Describes other files and folders that support the pipeline’s execution, schema management, and dataset organization.

* **.env.example** – local environment variable template
* **requirements.txt** - List of all Python dependencies required to run the pipeline.
* **Phase3.sql** - Defines the complete relational schema for PubMedFlo
* **reset.sql** - SQL utility script that truncates all the pipeline tables to reset the database while preserving schema.
* **artifacts/** - Contains all generated FAISS index artifacts for similarity search. The metadata file is compared against the current configuration, and the index is automatically regenerated if the embedding model or similarity metric changes.

### data/
* **raw/** - Contains 20 curated PubMed PDFs related to diabetes treatment, used as the input corpus for processing.
* **csv-diabetes-set.csv** - Stores the exported PubMed metadata corresponding to the 20 PDFs, used to populate the article and author tables.

---

## Requirements
Before running the repository locally, ensure you have the following installed:
* Python 3.11+
* PostgreSQL 15+
* FAISS (CPU)
* OpenAI API Key (optional for LLM generation)

---

## Dependencies & Setup
Install dependencies:
```bash
cd phase4
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```
* `PyPDF2` — PDF text extraction
* `psycopg` — PostgreSQL connector
* `sentence-transformers` — embedding model
* `faiss-cpu` — vector similarity index
* `openai` — LLM API that generates natural language responses
* `python-dotenv` - Loads environment variables from a `.env` file

### Initialize the Database Schema
* Run the schema file once to create all necessary tables:
```bash
psql "$PUBMEDFLO_DB_URL" -f Phase4.sql
```

### Environment Variables *(Optional)*
Copy the example environment file and add your OpenAI API key:
```bash
cp .env.example .env
```
Then open `.env` and set your credentials 
(API key can be obtained through [OpenAI Platform](https://platform.openai.com/api-keys)):
```bash
PUBMEDFLO_DB_URL="postgresql://<user>:<password>@localhost:5432/pubmedflo"
OPENAI_API_KEY=your_api_key_here
```
* **NOTE**: You will need to set up a payment method and add at least **$5 in credit** to your OpenAI account before the API key can be used for requests.

---

## Running the Pipeline
You can run the pipeline end-to-end or call its components individually.

```bash
# (A) End-to-end parse to build FAISS index
python3 pubmed_pipeline.py --log-level INFO

# (B) Optional standalone stages
python3 -m core.parse_directory --log-level INFO
python3 -m core.embed_chunks   --log-level INFO
python3 -m core.index_flat --build-only

# (C) Query FAISS index
python3 -m core.index_flat --query "best treatment for central diabetes insipidus" --k 5
python3 -m core.index_flat --metric cosine --query "best treatment for central diabetes insipidus" --k 5

# (D) LLM answer generation
python3 -m core.index_flat --answer --query "What is diabetes insipidus?" --k 5

# (E) Optional: Reset the database (clears all pipeline tables but preserves schema)
psql "$PUBMEDFLO_DB_URL" -f reset.sql
```


uvicorn backend.app:app --reload

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

Use `--answer` to see GPT‑4o-mini synthesize responses with inline `[PMID ######]` citations taken from the retrieved snippets.

---

## Verification
Some commands that verify that the pipeline successfully populated the database:

```bash
psql "$PUBMEDFLO_DB_URL" -c "SELECT COUNT(*) FROM text_chunks;"
psql "$PUBMEDFLO_DB_URL" -c "SELECT COUNT(*) FROM chunk_embeddings;"
psql "$PUBMEDFLO_DB_URL" -c "SELECT COUNT(*) FROM query_logs;"
psql "$PUBMEDFLO_DB_URL" -c "SELECT COUNT(*) FROM retrieves;"
```

---

## Results and Outputs
Below are example outputs and results based on the order of flow for the pipeline:
* `psql "$PUBMEDFLO_DB_URL" -f Phase3.sql`
```text
CREATE TABLE
CREATE TABLE
CREATE TABLE
CREATE TABLE
CREATE TABLE
CREATE TABLE
CREATE TABLE
CREATE TABLE
CREATE TABLE
CREATE TABLE
CREATE TABLE
CREATE TABLE
CREATE TABLE
```

* `python3 pubmed_pipeline.py --log-level INFO`
```text
INFO:root:=== Task 1: Parsing & Chunking ===
INFO:root:Inserted/updated 15 chunks for PMID 10612269
INFO:root:Processed 00002018-199921060-00002.pdf -> 15 chunks
INFO:root:Inserted/updated 31 chunks for PMID 22433947
INFO:root:Processed 000336333.pdf -> 31 chunks
INFO:root:Inserted/updated 15 chunks for PMID 38316255
INFO:root:Processed 1-s2.0-S0003426624000118-main.pdf -> 15 chunks
INFO:root:Inserted/updated 12 chunks for PMID 30454745
INFO:root:Processed 1-s2.0-S003139551830141X.pdf -> 12 chunks
INFO:root:Inserted/updated 20 chunks for PMID 32741486
INFO:root:Processed 1-s2.0-S0889852920300396.pdf -> 20 chunks
INFO:root:Inserted/updated 21 chunks for PMID 27156767
INFO:root:Processed 1-s2.0-S1521690X16000117-main.pdf -> 21 chunks
INFO:root:Inserted/updated 16 chunks for PMID 20500966
INFO:root:Processed 1-s2.0-S1701216316344486.pdf -> 16 chunks
INFO:root:Inserted/updated 25 chunks for PMID 36007536
INFO:root:Processed 1-s2.0-S2213858722002194.pdf -> 25 chunks
INFO:root:Inserted/updated 11 chunks for PMID 16444918
INFO:root:Processed 65.full.pdf -> 11 chunks
INFO:root:Inserted/updated 10 chunks for PMID 32383239
INFO:root:Processed Eur J Clin Investigation - 2020 - Clotman - Diabetes or endocrinopathy admitted in the COVID‐19 ward.pdf -> 10 chunks
INFO:root:Inserted/updated 10 chunks for PMID 26913870
INFO:root:Processed GIN_A33VS66_00232_1.pdf -> 10 chunks
INFO:root:Inserted/updated 47 chunks for PMID 36683321
INFO:root:Processed J Neuroendocrinology - 2023 - Angelousi - New developments and concepts in the diagnosis and management of diabetes.pdf -> 47 chunks
INFO:root:Inserted/updated 32 chunks for PMID 33713498
INFO:root:Processed Journal of Internal Medicine - 2021 - Christ‐Crain - Diagnosis and management of diabetes insipidus for the internist  an.pdf -> 32 chunks
INFO:root:Inserted/updated 26 chunks for PMID 34522399
INFO:root:Processed Management of Diabetes Insipidus following Surgery for Pituitary.pdf -> 26 chunks
INFO:root:Inserted/updated 18 chunks for PMID 25330715
INFO:root:Processed Pediatric Diabetes - 2014 - Karaa - The spectrum of clinical presentation  diagnosis  and management of mitochondrial forms.pdf -> 18 chunks
INFO:root:Inserted/updated 43 chunks for PMID 35771962
INFO:root:Processed dgac381.pdf -> 43 chunks
INFO:root:Inserted/updated 7 chunks for PMID 32005690
INFO:root:Processed pedsinreview_20180337.pdf -> 7 chunks
INFO:root:Inserted/updated 16 chunks for PMID 26742931
INFO:root:Processed s11892-015-0702-6.pdf -> 16 chunks
INFO:root:Inserted/updated 18 chunks for PMID 33527330
INFO:root:Processed s12020-021-02622-3.pdf -> 18 chunks
INFO:root:Inserted/updated 37 chunks for PMID 38693275
INFO:root:Processed s41574-024-00985-x.pdf -> 37 chunks
INFO:root:Processed 20/20 documents into 430 chunks
INFO:root:Database now holds 430 total chunks
INFO:root:=== Task 2: Embedding Generation ===
INFO:root:Loading model sentence-transformers/all-MiniLM-L6-v2
INFO:sentence_transformers.SentenceTransformer:Use pytorch device_name: mps
INFO:sentence_transformers.SentenceTransformer:Load pretrained SentenceTransformer: sentence-transformers/all-MiniLM-L6-v2
INFO:root:Encoding 430 chunks (batch_size=16)
Batches: 100%|█████████████████████████████████████████████████| 27/27 [00:03<00:00,  7.17it/s]
INFO:root:Stored 430 embeddings for model sentence-transformers/all-MiniLM-L6-v2
INFO:root:Embedding count matches chunk count (430)
INFO:root:=== Task 3: Building FAISS Index ===
INFO:root:Built FAISS index (430 vectors, dim=384) -> /Users/nathan/CS 480/phase3/artifacts/index_flat.faiss
INFO:root:Pipeline completed successfully.
```

* `python3 -m core.index_flat --query "best treatment for central diabetes insipidus" --k 5`
```text
INFO:root:FAISS index already up to date (model 'sentence-transformers/all-MiniLM-L6-v2', metric='euclidean').
INFO:root:Loaded FAISS index from /Users/nathan/CS 480/phase3/artifacts/index_flat.faiss
INFO:sentence_transformers.SentenceTransformer:Use pytorch device_name: mps
INFO:sentence_transformers.SentenceTransformer:Load pretrained SentenceTransformer: sentence-transformers/all-MiniLM-L6-v2
Batches: 100%|███████████████████████████████████████████████████| 1/1 [00:00<00:00,  4.67it/s]
INFO:root:Logged query: best treatment for central diabetes insipidus (query_id=1)
INFO:root:Top-5 results:
INFO:root:#1 score=0.6692 pmid=32741486 title=Diabetes Insipidus: An Update
INFO:root:#2 score=0.7403 pmid=34522399 title=Management of Diabetes Insipidus following Surgery for Pituitary and Suprasellar Tumours
INFO:root:#3 score=0.7463 pmid=38693275 title=Arginine vasopressin deficiency: diagnosis, management and the relevance of oxytocin deficiency
INFO:root:#4 score=0.7699 pmid=30454745 title=Nephrogenic Diabetes Insipidus
INFO:root:#5 score=0.7757 pmid=27156767 title=Diabetes insipidus in infants and children
```

* `python3 -m core.index_flat --metric cosine --query "best treatment for central diabetes insipidus" --k 5`
```text
INFO:root:Overriding metric type to 'cosine' via CLI flag.
INFO:root:Index built for euclidean but current metric is cosine. Rebuilding...
INFO:root:Built FAISS index (430 vectors, dim=384) -> /Users/nathan/CS 480/phase3/artifacts/index_flat.faiss
INFO:root:Loaded FAISS index from /Users/nathan/CS 480/phase3/artifacts/index_flat.faiss
INFO:sentence_transformers.SentenceTransformer:Use pytorch device_name: mps
INFO:sentence_transformers.SentenceTransformer:Load pretrained SentenceTransformer: sentence-transformers/all-MiniLM-L6-v2
Batches: 100%|███████████████████████████████████████████████████| 1/1 [00:00<00:00,  5.10it/s]
INFO:root:Logged query: best treatment for central diabetes insipidus (query_id=2)
INFO:root:Top-5 results:
INFO:root:#1 score=0.6654 pmid=32741486 title=Diabetes Insipidus: An Update
INFO:root:#2 score=0.6299 pmid=34522399 title=Management of Diabetes Insipidus following Surgery for Pituitary and Suprasellar Tumours
INFO:root:#3 score=0.6269 pmid=38693275 title=Arginine vasopressin deficiency: diagnosis, management and the relevance of oxytocin deficiency
INFO:root:#4 score=0.6150 pmid=30454745 title=Nephrogenic Diabetes Insipidus
INFO:root:#5 score=0.6122 pmid=27156767 title=Diabetes insipidus in infants and children
```

* `python3 -m core.index_flat --answer --query "What is diabetes insipidus?"`
```text
INFO:root:Index built for cosine but current metric is euclidean. Rebuilding...
INFO:root:Built FAISS index (430 vectors, dim=384) -> /Users/nathan/CS 480/phase3/artifacts/index_flat.faiss
INFO:root:Loaded FAISS index from /Users/nathan/CS 480/phase3/artifacts/index_flat.faiss
INFO:sentence_transformers.SentenceTransformer:Use pytorch device_name: mps
INFO:sentence_transformers.SentenceTransformer:Load pretrained SentenceTransformer: sentence-transformers/all-MiniLM-L6-v2
Batches: 100%|███████████████████████████████████████████████████| 1/1 [00:00<00:00,  3.80it/s]
INFO:httpx:HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
INFO:root:Generated answer with gpt-4o-mini:
Diabetes insipidus (DI) is a disorder characterized by the excretion of large amounts of dilute urine, leading to excessive thirst (polydipsia) and a significant loss of electrolytes and fluids. It is specifically defined by the production of hypotonic urine, with a daily output exceeding 50 mL/kg body weight and fluid intake often exceeding 3 liters per day [PMID 33713498].

There are several types of diabetes insipidus: 
1. **Central diabetes insipidus (CDI)** results from a deficiency of the hormone arginine vasopressin (AVP) due to damage to the pituitary gland or hypothalamus. This can arise from various causes, including tumors, trauma, infections, and autoimmune conditions.
2. **Nephrogenic diabetes insipidus (NDI)** occurs when the kidneys are resistant to the action of AVP, leading to the inability to concentrate urine despite normal hormone levels.
3. **Gestational diabetes insipidus** is linked to an increase in placental vasopressinase, which breaks down AVP.
4. **Primary polydipsia** involves excessive water intake independent of any dysfunction in AVP secretion or action [PMID 38316255].

Diagnosis involves a detailed medical history, physical examination, and specialized tests such as the water deprivation test, which assesses the body’s response to dehydration and helps differentiate between the different types of diabetes insipidus [PMID 33713498]. Treatment varies based on the underlying cause, particularly between CDI and NDI [PMID 35771962].
INFO:root:Logged query: What is diabetes insipidus? (query_id=3)
INFO:root:Top-5 results:
INFO:root:#1 score=0.5275 pmid=33713498 title=Diagnosis and management of diabetes insipidus for the internist: an update
INFO:root:#2 score=0.6291 pmid=38316255 title=Diabetes insipidus: Vasopressin deficiency…
INFO:root:#3 score=0.6931 pmid=35771962 title=Diagnosis and Management of Central Diabetes Insipidus in Adults
INFO:root:#4 score=0.6971 pmid=36683321 title=New developments and concepts in the diagnosis and management of diabetes insipidus (AVP-deficiency and resistance)
INFO:root:#5 score=0.7119 pmid=32005690 title=Diabetes Insipidus
```

* `python3 -m core.index_flat --answer --query "Founding of the US" --k 5` 
```text   
INFO:root:FAISS index already up to date (model 'sentence-transformers/all-MiniLM-L6-v2', metric='euclidean').
INFO:root:Loaded FAISS index from /Users/nathan/CS 480/phase3/artifacts/index_flat.faiss
INFO:sentence_transformers.SentenceTransformer:Use pytorch device_name: mps
INFO:sentence_transformers.SentenceTransformer:Load pretrained SentenceTransformer: sentence-transformers/all-MiniLM-L6-v2
Batches: 100%|███████████████████████████████████████████████████| 1/1 [00:00<00:00,  1.11it/s]
INFO:httpx:HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
INFO:root:Generated answer with gpt-4o-mini:
The context provided does not contain any information regarding the founding of the United States. Hence, I cannot answer your question.
INFO:root:Logged query: Founding of the US (query_id=4)
INFO:root:Top-5 results:
INFO:root:#1 score=1.8066 pmid=26913870 title=History of Diabetes Insipidus
INFO:root:#2 score=1.8380 pmid=22433947 title=Diabetes insipidus--diagnosis and management
INFO:root:#3 score=1.8455 pmid=26913870 title=History of Diabetes Insipidus
INFO:root:#4 score=1.8925 pmid=38693275 title=Arginine vasopressin deficiency: diagnosis, management and the relevance of oxytocin deficiency
INFO:root:#5 score=1.8957 pmid=27156767 title=Diabetes insipidus in infants and children
```

* `psql "$PUBMEDFLO_DB_URL" -f reset.sql`
```text
BEGIN
TRUNCATE TABLE
COMMIT
    table_name    | estimated_rows 
------------------+----------------
 chunk_embeddings |             -1
 curators         |             -1
 documents        |             -1
 pubmed_articles  |             -1
 pubmed_authors   |             -1
 query_logs       |             -1
 retrieves        |             -1
 text_chunks      |             -1
 users            |             -1
(9 rows)
```