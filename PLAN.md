Below is the cleaned, professional **`plan.md`**, with **no emojis**, pure Markdown, and a **CSS structure split by page/component** instead of a single CSS file.

---

# Phase 4 + Bonus Plan

## Full System Integration + Simple CSS UI (2–3 Day Schedule)

Project: Question-Answering System — CS 480
UI Requirement: Normal CSS (no Tailwind)

## Overview

This document defines the milestones and tasks required to complete Phase 4 of the project along with the bonus UI component. The plan is optimized for a 2–3 day completion window and assumes the Phase 3 vector pipeline is already implemented and stable.

The system must integrate:

* User authentication and role management
* SQL CRUD operations
* Document upload and processing
* Chunking, embedding, and vector storage
* Querying with retrieval and LLM generation
* Logging and admin operations
* A simple, clean HTML/CSS frontend

---

# Milestones

## Milestone 1: Backend Foundations (5–7 hours)

**Goal:** Establish authentication, role-based access, and core SQL CRUD functionality.

### Tasks

* Implement routes:

  * `POST /signup`
  * `POST /login`
  * `GET /admin/users`
  * `PUT /admin/users/<id>`
  * `DELETE /admin/users/<id>`
* Implement password hashing (bcrypt)
* Add JWT or session-based authentication
* Finalize SQL tables:

  * `users`
  * `roles`
  * `documents`
  * `query_logs`
* Add middleware for role enforcement (admin/curator/user)

### Deliverables

* Fully working login and signup
* Role-based protected routes
* SQL user management tested and functional

---

## Milestone 2: Curator Document Pipeline Integration (5–7 hours)

**Goal:** Connect document upload to the existing vector pipeline.

### Tasks

* Add `POST /curator/upload` endpoint
* Integrate Phase 3:

  * PDF → text → chunks
  * chunks → embeddings
  * embeddings → vector store
  * document metadata → SQL
* Add `DELETE /curator/documents/<doc_id>`
* Add `GET /curator/documents`
* Implement vector reload logic on server startup
* Ensure persistence across restarts

### Deliverables

* Uploading a document automatically updates vector store
* Documents can be listed and deleted
* Metadata stored in SQL
* Embeddings and vectors survive server restarts

---

## Milestone 3: End User Query Flow (3–4 hours)

**Goal:** Provide a complete search → retrieval → LLM answer workflow.

### Tasks

* Implement `POST /query`
* Use FAISS/pgvector for k-NN search
* Call LLM (gpt-4o-mini or similar) with citations
* Record query logs in SQL
* Return JSON response containing:

  * `answer`
  * `citations`
  * `retrieved_chunks`

### Deliverables

* Functional question-answer system
* Query logs saved to database
* Answers with citations returned to UI

---

## Milestone 4: Bonus UI (HTML Templates + Split CSS) (7–10 hours)

**Goal:** Build a clean, minimal UI with split CSS files instead of one global file.

### Required Pages

1. Login Page
2. Signup Page
3. Admin Dashboard
4. Curator Dashboard
5. Search Page
6. Shared components (nav bar, header)

### CSS Structure (split by page or component)

```
static/css/
│
├── base/
│   ├── reset.css
│   ├── layout.css
│   └── typography.css
│
├── components/
│   ├── buttons.css
│   ├── forms.css
│   ├── tables.css
│   └── navbar.css
│
└── pages/
    ├── login.css
    ├── signup.css
    ├── admin_dashboard.css
    ├── curator_dashboard.css
    └── search.css
```

### HTML Template Structure

```
templates/
│
├── layout.html        (master template)
├── login.html
├── signup.html
├── admin_dashboard.html
├── curator_dashboard.html
└── search.html
```

### Tasks

* Build layout system using Jinja templates
* Implement CSS per page/component
* Add:

  * Login form
  * Signup form
  * Admin user table
  * Curator upload form + table
  * Search interface with answer/citation sections
* Ensure role-based routing on login

### Deliverables

* Clean, functional, non-Tailwind UI
* Separate CSS files for maintainability
* Appropriate styling for readability and grading clarity

---

## Milestone 5: Final QA and Demo Preparation (2 hours)

**Goal:** Verify all user scenarios defined in the project specification.

### Required Test Scenarios

* New user signup
* Login
* Admin lists all users
* Admin edits a user
* Admin deletes a user
* Curator uploads a document
* Curator deletes a document
* End user submits a query and receives a valid answer
* Newly uploaded documents immediately appear in search
* Query logs stored and retrievable
* All operations persist after restart

### Deliverables

* Fully working system
* Ready for demo recording
* No broken routes

---

# 2–3 Day Timeline

## Day 1 (6–8 hours)

* Complete Milestone 1
* Complete half of Milestone 2 (upload endpoint + metadata + pipeline integration)

## Day 2 (6–8 hours)

* Finish Milestone 2
* Complete Milestone 3
* Begin UI (login/signup + layout + base CSS)

## Day 3 (6–8 hours)

* Complete UI pages
* Finish all CSS files
* Complete Milestone 5
* Full system test and error cleanup

---

# Recommended Folder Structure

```
project/
│
├── backend/
│   ├── app.py
│   ├── auth.py
│   ├── admin.py
│   ├── curator.py
│   ├── query.py
│   ├── database/
│   │   ├── models.py
│   │   ├── repository.py
│   │   └── init.sql
│   └── services/
│       └── pipeline_service.py
│
├── templates/
│   ├── layout.html
│   ├── login.html
│   ├── signup.html
│   ├── admin_dashboard.html
│   ├── curator_dashboard.html
│   └── search.html
│
└── static/
    └── css/
        ├── base/
        ├── components/
        └── pages/
```

---

If you'd like, I can now generate:

* All template HTML files
* Split CSS boilerplate
* Backend route stubs matching this structure
* A minimal working FastAPI or Flask skeleton with auth and templating

Just tell me what to generate next.


* Reviewing and adding comments to the code:
currently on repository.py
roadmap: app (before include router) -> auth -> admin
and then I need to do milestone 2
