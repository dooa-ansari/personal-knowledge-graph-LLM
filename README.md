# Django RDF Semantic Resume Agent 🧠🕸️

A lightweight Django service that combines **RDF/Turtle (.ttl)** data modeling, local **SPARQL** querying via `rdflib`, and session-aware **RAG** through **ChromaDB**, **LangGraph**, and **OpenRouter**.

Instead of dumping raw documents or bloated text chunks into an LLM context window, this project implements a precise **GraphRAG-lite** pattern: translating natural language questions into deterministic SPARQL graph queries to eliminate hallucinations and extract exact background data.

---

## 🚀 Architecture & Workflow

1. **Semantic Ingestion:** Candidate details and skill networks are structured into standard ontologies (such as Schema.org's `schema:Person`) and serialized as compact **RDF Turtle (`.ttl`)**.
2. **Intent Translation:** The user types a natural language prompt into the Django interface. The LLM translates this prompt into a precise **SPARQL SELECT query**.
3. **Local Execution:** Python's `rdflib` runs the SPARQL query locally against the in-memory `.ttl` graph, ensuring 100% data grounding and factual alignment.
4. **Natural Language Synthesis:** The precise query results are passed back to the LLM to synthesize a professional, context-aware answer for the user.

The project also provides a vector RAG path. Resume entities are indexed as contextual chunks in ChromaDB. A LangGraph workflow stores conversation state, rewrites follow-up questions into standalone retrieval queries, retrieves the most relevant chunks, and generates an answer grounded only in those chunks.

---

## 🛠️ Tech Stack

* **Backend:** Python, Django 5.2 (LTS)
* **Semantic Graph Engine:** `rdflib` 7.1 (RDF parsing and SPARQL 1.1 engine)
* **LLM Orchestration:** OpenAI-compatible API via OpenRouter (`requests` library)
* **AI Model:** Inclusion AI Ling 3.0 Flash via OpenRouter (`inclusionai/ling-3.0-flash`) — configured centrally in `resume_api/services/model_config.py`
* **Vector Retrieval:** ChromaDB persistent collection with OpenRouter embeddings
* **RAG Orchestration:** LangGraph `StateGraph` with `MemorySaver` session checkpoints
* **API Documentation:** Swagger / OpenAPI via `drf-yasg`
* **Environment Management:** `python-dotenv`

---

## 📁 Project Structure

```
personal-knowledge-graph/
├── manage.py
├── requirements.txt
├── .env                        # OpenRouter API config (git-ignored)
├── .env.example                # Template for .env
├── .gitignore
├── All Details Resume.md      # Source resume markdown file
├── All Details Resume.ttl     # Generated RDF knowledge graph
├── config/                    # Django project configuration
│   ├── settings.py            # Settings (loads .env, registers apps)
│   ├── urls.py                # Root URL routing + Swagger
│   ├── asgi.py
│   └── wsgi.py
├── core/                      # Core app (home page)
│   ├── views.py
│   └── urls.py
└── resume_api/                # Resume API app
    ├── views.py               # API endpoints + system prompts
    ├── urls.py                # API URL routing
│   ├── serializers.py         # DRF serializers for Swagger
│   ├── tests.py               # 57 unit tests
    └── services/
        ├── rdf_converter.py   # Resume markdown → RDF converter
        ├── openrouter_service.py  # OpenRouter LLM client
        ├── sparql_service.py  # SPARQL query execution engine
        ├── langgraph_service.py   # LangGraph conversational search
        ├── rag_langgraph_service.py # Session-aware RAG workflow + query rewriting
        ├── rag_indexer.py         # RDF entities → contextual vector chunks
        ├── vector_search_service.py # ChromaDB semantic retrieval
        ├── rag_answer_service.py   # Stateless grounded RAG orchestration
        ├── simple_search_service.py  # Stateless one-shot search
        └── model_config.py    # Central model configuration (single source of truth)
```

---

## 🔧 Installation

### Prerequisites

* Python 3.10+
* pip

### Steps

1. **Clone the repository:**
   ```bash
   git clone <your-repo-url>
   cd personal-knowledge-graph
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables:**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and replace `your-openrouter-api-key-here` with your actual OpenRouter API key:
   ```env
   OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
   OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxx
   ```

4. **Run database migrations:**
   ```bash
   python3 manage.py migrate
   ```

5. **Build the RAG index:**
   ```bash
   python3 manage.py reindex_rag
   ```

   Re-run this command whenever `All Details Resume.ttl` or the chunking logic changes. Bullet-point chunks include their parent company, role, dates, and location so related responsibilities can be retrieved reliably.

---

## ▶️ Execution

### Start the development server

```bash
python3 manage.py runserver
```

The server will start at `http://127.0.0.1:8000/`.

### Generate the RDF knowledge graph

```bash
curl -X POST http://127.0.0.1:8000/api/convert-resume/
```

This reads `All Details Resume.md`, converts it to RDF, and writes `All Details Resume.ttl` in the same directory.

### Search the knowledge graph (with conversation context)

```bash
curl -X POST http://127.0.0.1:8000/api/search-knowledge-graph/ \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What companies has the candidate worked at?"}'
```

**Example response:**
```json
{
  "prompt": "What companies has the candidate worked at?",
  "model": "inclusionai/ling-3.0-flash",
  "sparql_query": "PREFIX resume: <http://example.org/resume#> SELECT ?company WHERE { ... }",
  "query_results": {
    "columns": ["company"],
    "rows": [
      {"company": "DeepSkill GmbH"},
      {"company": "Greator GmbH"},
      {"company": "Mindshine GmbH"},
      {"company": "VentureDive"},
      {"company": "Centegy Technologies"},
      {"company": "Digital Dividend"}
    ],
    "row_count": 6
  },
  "answer": "The candidate has worked at 6 companies: DeepSkill GmbH, Greator GmbH, Mindshine GmbH, VentureDive, Centegy Technologies, and Digital Dividend."
}
```

### Search the knowledge graph (stateless, one-shot)

For a single question/answer with no conversation context or session tracking:

```bash
curl -X POST http://127.0.0.1:8000/api/search-knowledge-graph-simple/ \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What companies has the candidate worked at?"}'
```

**Example response:**
```json
{
  "prompt": "What companies has the candidate worked at?",
  "model": "inclusionai/ling-3.0-flash",
  "sparql_query": "PREFIX resume: <http://example.org/resume#> SELECT ?company WHERE { ... }",
  "query_results": {
    "columns": ["company"],
    "rows": [
      {"company": "DeepSkill GmbH"},
      {"company": "Greator GmbH"},
      {"company": "Mindshine GmbH"},
      {"company": "VentureDive"},
      {"company": "Centegy Technologies"},
      {"company": "Digital Dividend"}
    ],
    "row_count": 6
  },
  "answer": "The candidate has worked at 6 companies: DeepSkill GmbH, Greator GmbH, Mindshine GmbH, VentureDive, Centegy Technologies, and Digital Dividend."
}
```

> **Note:** The simple endpoint returns no `session_id` — each request is fully independent.

### Session-aware semantic RAG search

Use `/api/search-rag/` for vector retrieval and conversational follow-ups:

```bash
curl -X POST http://127.0.0.1:8000/api/search-rag/ \
  -H "Content-Type: application/json" \
  -d '{"prompt": "When did Dooa work at Greator?"}'
```

The first response contains a generated `session_id` and the `retrieval_query`. Reuse the session ID for follow-up questions:

```bash
curl -X POST http://127.0.0.1:8000/api/search-rag/ \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What did she do there?", "session_id": "<session-id-from-response>"}'
```

The request body accepts only `prompt` and optional `session_id`. Retrieval size is controlled server-side by `RAG_TOP_K`.

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/convert-resume/` | Convert resume markdown to RDF (.ttl) |
| `POST` | `/api/search-knowledge-graph/` | Search knowledge graph with AI + conversation context (LangGraph, session-based) |
| `POST` | `/api/search-knowledge-graph-simple/` | Search knowledge graph with AI (stateless, one-shot, no session) |
| `POST` | `/api/search-rag/` | Session-aware vector RAG with LangGraph query rewriting |
| `GET` | `/swagger/` | Swagger UI (interactive API documentation) |
| `GET` | `/redoc/` | ReDoc UI (alternative API documentation) |
| `GET` | `/swagger.json` | Swagger JSON schema |
| `GET` | `/swagger.yaml` | Swagger YAML schema |
| `GET` | `/` | Home page |

---

## 🔍 How the Knowledge Graph Search Works

```mermaid
flowchart TD
    A[User Prompt] --> B["Step 1: SPARQL Generation<br/>OpenRouter (Inclusion AI Ling 3.0 Flash)<br/>with SPARQL_SYSTEM_PROMPT"]
    B --> C["Step 2: SPARQL Execution<br/>rdflib (local, deterministic)<br/>against All Details Resume.ttl"]
    C --> D["Step 3: Natural Language Synthesis<br/>OpenRouter (Inclusion AI Ling 3.0 Flash)<br/>with NATURAL_LANGUAGE_SYSTEM_PROMPT"]
    D --> E[API Response]

    style A fill:#4CAF50,color:#fff
    style B fill:#2196F3,color:#fff
    style C fill:#FF9800,color:#fff
    style D fill:#9C27B0,color:#fff
    style E fill:#4CAF50,color:#fff
```

---

## 🔄 LangGraph Workflow (Conversational Search)

The `/api/search-knowledge-graph/` endpoint is orchestrated by a **LangGraph StateGraph** built in `resume_api/services/langgraph_service.py`. Unlike a single-shot pipeline, this workflow maintains conversation context across turns using a `MemorySaver` checkpointer keyed by `thread_id` (the client-provided `session_id`).

The line `workflow.set_entry_point("generate_sparql")` declares **where execution starts**: the **`generate_sparql`** node. Edges alone only describe transitions between nodes; this line anchors the graph so that `_compiled_workflow.invoke(...)` always begins at the SPARQL-generation step.

```mermaid
flowchart TD
    StartNode["🟢 START"] --> SparqlNode["generate_sparql 🔵 (entry point)<br/>LLM: conversation history → SPARQL query<br/>via SPARQL_SYSTEM_PROMPT"]
    SparqlNode --> ValidateNode["validate_sparql 🟡<br/>rdflib parses query syntax<br/>stores valid/error state"]
    ValidateNode -->|"valid"| ExecNode["execute_sparql 🟠<br/>rdflib runs query on All Details Resume.ttl<br/>stores results in state"]
    ValidateNode -->|"invalid + attempts remaining"| SparqlNode
    ValidateNode -->|"invalid + retry limit reached"| InvalidNode["invalid_sparql 🔴<br/>raises validation error"]
    ExecNode --> AnsNode["generate_answer 🟣<br/>LLM: results → natural language answer<br/>appends AIMessage to history"]
    AnsNode --> EndNode["🔴 END"]
    InvalidNode --> ErrorEnd["🔴 ERROR"]
    AnsNode --> RespNode["🟢 API Response<br/>sparql_query / query_results / answer"]

    subgraph Memory["Persisted state (MemorySaver, thread_id = session_id)"]
        StateNode["GraphState: messages, sparql_query,<br/>query_results, answer, attempts, error, valid"]
    end

    AnsNode -->|"saves state"| StateNode
    SparqlNode -.->|"loads conversation history"| StateNode

    style StartNode fill:#4CAF50,color:#fff
    style SparqlNode fill:#2196F3,color:#fff
    style ValidateNode fill:#FFC107,color:#000
    style ExecNode fill:#FF9800,color:#fff
    style AnsNode fill:#9C27B0,color:#fff
    style EndNode fill:#F44336,color:#fff
    style InvalidNode fill:#F44336,color:#fff
    style ErrorEnd fill:#F44336,color:#fff
    style StateNode fill:#607D8B,color:#fff
    style RespNode fill:#4CAF50,color:#fff
```

Each user turn follows **generate → validate → execute → answer**. If validation fails, the conditional edge sends the workflow back to `generate_sparql` while attempts remain; after the retry limit, `invalid_sparql` raises a clear error. The dashed lines show how prior turns and retry state are loaded from and saved to the checkpointer, enabling follow-ups like *"What did she do there?"*.

## 🔎 LangGraph Workflow (Session-aware RAG)

The `/api/search-rag/` endpoint uses a separate workflow in `resume_api/services/rag_langgraph_service.py`:

```mermaid
flowchart TD
    Start["🟢 START<br/>session_id + prompt"] --> Rewrite["🔵 rewrite_query<br/>LLM resolves pronouns and references<br/>conversation → standalone query"]
    Rewrite --> Retrieve["🟠 retrieve<br/>OpenRouter embedding<br/>ChromaDB top-K search"]
    Retrieve --> Answer["🟣 answer<br/>LLM uses conversation + retrieved context<br/>grounded response"]
    Answer --> End["🔴 END<br/>answer + retrieval_query + chunks"]

    subgraph Memory["LangGraph MemorySaver<br/>thread_id = session_id"]
        State["messages<br/>retrieval_query<br/>retrieved_chunks<br/>answer"]
    end

    State -.-> Rewrite
    Answer -.-> State

    style Start fill:#4CAF50,color:#fff
    style Rewrite fill:#2196F3,color:#fff
    style Retrieve fill:#FF9800,color:#fff
    style Answer fill:#9C27B0,color:#fff
    style End fill:#F44336,color:#fff
    style State fill:#607D8B,color:#fff
```

The rewrite node is an LLM call, but it uses the existing configured model. It is intentionally separate from retrieval: conversation history is retained for context resolution, while ChromaDB receives one focused standalone query instead of a concatenation of previous topics.

---

## 🧪 Testing

Run the full test suite (57 tests):

```bash
python3 manage.py test resume_api -v 2
```

**Test coverage:**

| Test Class | Tests | Description |
|------------|-------|-------------|
| `RDFConverterServiceTests` | 11 | RDF converter parsing functions |
| `ResumeApiEndpointTests` | 6 | Convert-resume endpoint |
| `OpenRouterServiceTests` | 4 | OpenRouter API client |
| `SparqlServiceTests` | 6 | SPARQL execution engine |
| `SearchKnowledgeGraphEndpointTests` | 7 | Search endpoint (success, errors, method validation) |
| `LangGraphServiceTests` | 3 | LangGraph conversational search service |
| `SimpleSearchServiceTests` | 3 | Stateless one-shot search service |
| `SimpleSearchEndpointTests` | 6 | Stateless search endpoint |
| `SwaggerEndpointTests` | 4 | Swagger/ReDoc documentation |
| `RagSearchEndpointTests` | 4 | Session-aware RAG API validation |
| `RagLangGraphServiceTests` | 2 | Query rewriting, retrieval, and session history |

---

## 📊 RDF Knowledge Graph Ontology

The knowledge graph uses the following namespaces:

| Prefix | URI |
|--------|-----|
| `foaf` | `http://xmlns.com/foaf/0.1/` |
| `schema` | `https://schema.org/` |
| `resume` | `http://example.org/resume#` |
| `rdf` | `http://www.w3.org/1999/02/22-rdf-syntax-ns#` |

**Entity types:**

| Type | Properties |
|------|------------|
| `foaf:Person` | `foaf:name`, `schema:jobTitle` |
| `resume:ProfessionalExperience` | `resume:company`, `resume:location`, `resume:dates`, `resume:role`, `resume:hasBulletPoint` |
| `resume:BulletPoint` | `rdf:value` |
| `resume:Education` | `resume:institution`, `resume:dates`, `schema:educationalCredentialAwarded` |
| `resume:Language` | `resume:language`, `resume:proficiency` |
| `resume:AcademicExperience` | `schema:name`, `resume:year`, `resume:location`, `resume:challenge`, `resume:technologyStack`, `resume:outcome`, `schema:url` |
| `resume:SkillCategory` | `resume:skillCategory`, `resume:hasSkill` |
| `resume:Skill` | `rdf:value` |
| `resume:SkillDetail` | `schema:name`, `resume:hasSkillItem` |
| `resume:SkillItem` | `rdf:value` |
| `resume:Project` | `schema:name` |

---

## 📦 Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| Django | 5.2.16 | Web framework |
| rdflib | 7.1.1 | RDF parsing & SPARQL engine |
| djangorestframework | 3.17.1 | REST API framework |
| drf-yasg | 1.21.15 | Swagger/OpenAPI documentation |
| python-dotenv | 1.0.1 | Environment variable loading |
| `requests` | 2.31.0 | HTTP client for OpenRouter API |
| `langgraph` | 1.2.10 | Stateful workflow orchestration |
| `langchain-core` | 1.5.3 | Message and graph primitives |
| `chromadb` | 0.6.3+ | Persistent vector database |
| `openai` | 2.x | OpenRouter-compatible embeddings client |

---

## 🔐 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENROUTER_BASE_URL` | OpenRouter API base URL | `https://openrouter.ai/api/v1` |
| `OPENROUTER_API_KEY` | Your OpenRouter API key | (required) |
| `EMBEDDING_MODEL` | OpenRouter-compatible embedding model | `openai/text-embedding-3-small` |
| `CHROMA_PERSIST_PATH` | Persistent ChromaDB storage path | `./data/chroma` |
| `RAG_COLLECTION_NAME` | ChromaDB collection name | `resume_chunks` |
| `RAG_TOP_K` | Number of chunks passed to the RAG answer model | `2` |

---

## 📄 License

This project is licensed under the BSD License.