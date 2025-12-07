# **Product Discovery Assistant (AI-Powered Fashion Recommender)**

**TL;DR:**
A full-stack AI Product Discovery system that scrapes clothing products from Hunnit.com using ScraperAPI, stores them in PostgreSQL (Neon), indexes them in Qdrant, enriches them with a Neo4j Knowledge Graph, and serves intelligent outfit recommendations via a FastAPI backend and a modern React frontend.

Prototype link: https://product-discovery-assistant-ochre.vercel.app/

<img width="797" height="638" alt="image" src="https://github.com/user-attachments/assets/e61f2907-17d0-4927-87e3-ac62c1ba23b0" />

---

# **Table of Contents**

1. [Overview](#overview)
2. [Features](#features)
3. [Folder Structure](#folder-structure)
4. [How to Run Locally](#how-to-run-locally)

   * Backend setup
   * Frontend setup
   * Environment variables
   * Database setup
   * Example API requests
   * Docker instructions
5. [Architecture & Design Decisions](#architecture--design-decisions)

   * Mermaid Diagram
6. [Scraping Approach (ScraperAPI + BeautifulSoup)](#scraping-approach-scraperapi--beautifulsoup)
7. [RAG Pipeline Design](#rag-pipeline-design)
8. [Knowledge Graph (Neo4j) Design](#knowledge-graph-neo4j-design)
9. [Challenges & Trade-Offs](#challenges--trade-offs)
10. [Testing, CI/CD, & Code Quality](#testing-cicd--code-quality)
11. [Security & Privacy Notes](#security--privacy-notes)
12. [Performance & Deployment Considerations](#performance--deployment-considerations)
13. [Improvements (Prioritized)](#improvements-prioritized)
14. [Appendices](#appendices)

* Checklist
* FAQ
* Example docker-compose.yml

15. [Hindi Summary (हिंदी सारांश)](#हिंदी-सारांश)

---

#  **Overview**

This project is an **AI-powered product discovery assistant** for clothing.
It:

* Scrapes product data from **Hunnit.com** using **ScraperAPI + BeautifulSoup**
* Stores structured product info (title, price, features, image URL, category…) in **Neon PostgreSQL**
* Generates **semantic embeddings** using *sentence-transformers/all-MiniLM-L6-v2*
* Indexes them in **Qdrant Vector DB**
* Builds a **Knowledge Graph** in Neo4j (products → categories → features)
* Uses a hybrid **RAG + KG + LLM** reasoning pipeline for smart outfit recommendations
* Serves results through a **FastAPI backend**
* Provides a clean, responsive frontend built with **React + Tailwind**

The result is an end-to-end mini “AI stylist” capable of answering queries like:

> “Show me oversized hoodies under 2000 for gym.”

---

#  **Folder Structure**

```
product-discovery-assistant/
│
├── backend/
│   ├── app/
│   │   ├── api/v1/         # FastAPI routes (products, search, scrape, health)
│   │   ├── core/           # Settings & configuration
│   │   ├── db/             # DB engine, session, Base
│   │   ├── models/         # SQLAlchemy models
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── services/       # embeddings, llm, scraper, graph, products
│   │   └── main.py         # FastAPI app factory & startup hooks
│   ├── Data_Scraping/
│   │   └── scrap.py        # ScraperAPI-based Hunnit scraper
│   ├── create_db.py
│   ├── Dockerfile
│   ├── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/     # Header, ProductCard
│   │   ├── pages/          # Home, Chat, ProductDetail
│   │   ├── api.js          # API wrapper for FastAPI
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   ├── index.css
│   ├── public/
│   ├── package.json
│   ├── tailwind.config.js
│
└── README.md
```

---

#  **How to Run Locally**

---

## **1. Backend Setup**

### **Install dependencies**

```bash
cd backend
pip install -r requirements.txt
```

### **Create `.env` file**

(Your backend **requires** these variables.)

```
# --- Database (Neon Postgres) ---
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST/dbname

# --- Qdrant Vector DB ---
QDRANT_URL=https://your-qdrant-url
QDRANT_API_KEY=your_qdrant_key
QDRANT_COLLECTION=products_collection_minilm

# --- ScraperAPI ---
SCRAPER_API_KEY=your_scraperapi_key

# --- LLM Keys ---
GROQ_API_KEY=your_groq_key
OPENAI_API_KEY=your_openai_key

# --- Neo4j Knowledge Graph ---
NEO4J_ENABLED=True
NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
```

### **Initialize DB tables**

```bash
python create_db.py
```

### **Run FastAPI**

```bash
uvicorn app.main:app --reload
```

Your backend will be available at:

`http://127.0.0.1:8000/api/v1`

---

## **2. Frontend Setup**

```bash
cd frontend
npm install
npm run dev
```

Set `.env` for frontend:

```
VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

The app runs at:

 `http://localhost:5173`

---

## **3. Scraping (Hunnit.com via ScraperAPI)**

Trigger scrape:

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/scrape/hunnit?max_products=40"
```

---

## **4. Example Search Request**

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "show me oversized hoodies under 2000"}'
```

---

## **5. Docker Instructions**

### **Build image**

```bash
docker build -t product-backend .
```

### **Run**

```bash
docker run -p 8000:8000 --env-file .env product-backend
```

---

#  **Architecture & Design Decisions**

The system integrates:

* **FastAPI** — high-performance async backend, clean routing structure
* **ScraperAPI + BeautifulSoup** — highly reliable scraping without IP blocks
* **Neon PostgreSQL** — scalable cloud Postgres database
* **Qdrant** — vector similarity search for semantic retrieval
* **Neo4j** — conceptual reasoning using graph structure
* **SentenceTransformers** — lightweight multilingual embeddings
* **Groq + OpenAI** — LLM reasoning with fallback model
* **React + Tailwind** — clean modern UX

---

## **Mermaid Architecture Diagram**

```mermaid
flowchart TD

A[ScraperAPI] --> B[Data_Scraping/scrap.py<br>BeautifulSoup Parsing]
B --> C[Neon PostgreSQL<br>Products Table]

C --> D[FastAPI Backend]

D --> E[Embeddings Service<br>SentenceTransformer]
E --> F[Qdrant Vector DB]

C --> G[Neo4j Knowledge Graph]
G --> D

D --> H[Search API<br>Hybrid RAG+KG]

H --> I[Groq/OpenAI LLM]

I --> J[Frontend React App<br>Home / Chat / Product Detail]

J --> D
```

---

#  **Scraping Approach (ScraperAPI + BeautifulSoup)**

### **Files**

* `Data_Scraping/scrap.py`
* `app/services/scraper.py`

### **Key points**

✔ Uses **ScraperAPI** to bypass anti-bot systems:

```python
SCRAPER_API_BASE = "http://api.scraperapi.com"
```

✔ HTML parsed using **BeautifulSoup**

✔ Selectors rely on:

* `<a href="/products/...">` for product listing
* `<h1>` for titles
* Regex for price detection
* Headings like “Product Features” for structured bullet extraction

✔ Cleaned description is generated using:

```python
build_clean_description()
```

✔ Data stored directly into **PostgreSQL** via SQLAlchemy ORM.

###  Missing Politeness Measures (Needs Improvement)

* No robots.txt check
* No delay/backoff between requests
* No proxy rotation (ScraperAPI handles some of this)

---

#  **RAG Pipeline Design**

### Components:

| Component    | File                     | Responsibility                   |
| ------------ | ------------------------ | -------------------------------- |
| Scraper      | `scrap.py`               | Collect raw product data         |
| Embedder     | `services/embeddings.py` | Encode with SentenceTransformer  |
| Vector DB    | Qdrant                   | Semantic similarity              |
| KG           | `services/graph.py`      | Category & feature relationships |
| LLM          | `services/llm.py`        | Final answer generation          |
| Search Logic | `api/v1/search.py`       | Hybrid rank + LLM rerank         |

---

## **Pipeline Stages**

### **1. Scraper → DB**

```python
parse_hunnit_product(url)
```

### **2. DB → Embeddings → Qdrant**

```python
index_all_products(db, skip_if_indexed=True)
```

### **3. Query → Intent Detection → KG Filtering**

* category synonyms
* tag extraction
* price extraction

### **4. Semantic Search (Qdrant)**

```python
semantic_search(enriched_query)
```

### **5. KG Context Extraction**

```python
get_kg_context_for_products()
```

### **6. LLM Answer with RAG**

```python
answer_with_rag(question, rag_chunks)
```

### **7. Final Re-ranking**

---

## **LLM Prompt Template**

```text
You are an AI fashion stylist. You must recommend outfits ONLY using the 
products listed in the context below.

Rules:
- Suggest 2–4 suitable products.
- If no exact match exists, recommend closest alternatives.
- Keep answer short.

Context:
{{RAG_CHUNKS}}

User query: {{QUESTION}}

Now give a friendly recommendation:
```

---

#  **Knowledge Graph (Neo4j) Design**

<img width="645" height="562" alt="image" src="https://github.com/user-attachments/assets/2ba76a6b-ffb9-421c-b9f9-42c68e2577ea" />

Nodes:

* `Product`
* `Category`
* `Feature`

Relationships:

* `Product → BELONGS_TO → Category`
* `Product → HAS_FEATURE → Feature`

Used for:

* enrichment of context
* filtering candidates
* semantic expansion

---

#  **Challenges & Trade-Offs**

### 1. Scraper Reliability

ScraperAPI improves reliability but costs money.

**Alternative:** Playwright + proxies.

---

### 2. Embedding Cost & Latency

Batch encoding solves speed but initial startup still heavy.

**Alternative:** Precompute embeddings or store them in DB.

---

### 3. Knowledge Graph Sync

Currently skips re-sync if data exists.

**Trade-off:** Faster startup vs potentially stale KG.

---

### 4. LLM Costs

Groq is cheaper, fallback to OpenAI.

---

### 5. Vector DB Consistency

If products are updated, embeddings must be re-indexed manually.

---

#  **Tests, CI/CD, Code Quality**

No test suite present → recommend:

* pytest
* CI pipeline (GitHub Actions)
* black + flake8 linting

---

#  **Security & Privacy Notes**

✔ API keys must stay in `.env`
❌ NO keys should be committed (verify before publishing)
✔ Rotate keys if exposed

---

#  **Performance & Deployment Considerations**

* Use **Render** for backend
* Use **Vercel** for frontend
* Enable Qdrant sharding for >50k products
* Use background worker to scrape periodically
* Cache embeddings to reduce recomputation

---

#  **Improvements (Prioritized)**

### **Short-term**

1. Add retry + exponential backoff to scraping
2. Add alembic migrations
3. Cache search responses

### **Medium-term**

4. Incremental embedding update instead of full reindex
5. Pagination on products API
6. Multi-vendor scraping (Furlenco, Traya, etc.)

### **Long-term**

7. User profiling (preferences, sizes, style)
8. Real-time KG updates
9. A/B testing for recommendation quality
