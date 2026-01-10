YOU (Browser)
│
▼
┌─────────────────────────────────────────────────────────────┐
│ API LAYER │
│ (FastAPI Routers → interface.py → Engine) │
└─────────────────────────────────────────────────────────────┘
│ ▲
│ add_memory() │ SSE Stream (events)
▼ │
╔═════════════════════════════════════════════════════════════╗
║ THE ENGINE (THE BOX) ║
║ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌──────────┐ ║
║ │ Embedder │ │ Memory │ │ Antisym │ │ Math │ ║
║ └───────────┘ └───────────┘ └───────────┘ └──────────┘ ║
║ ┌───────────────────────┐ ┌───────────────────────────┐ ║
║ │ Evolution Scheduler │ │ Invention Scheduler │ ║
║ │ (Background Thread) │ │ (Background Thread) │ ║
║ └───────────────────────┘ └───────────────────────────┘ ║
╚═════════════════════════════════════════════════════════════╝
│ │
│ store.upsert_node() │ emit_evolution_event()
▼ ▼
┌─────────────────────┐ ┌─────────────────────┐
│ DATA LAYER │ │ EVENTS.PY │
│ (Storage) │ │ (Signal Bus) │
│ ┌───────────────┐ │ └─────────────────────┘
│ │ PostgresStore │───────────▶ PostgreSQL DB
│ │ QdrantStore │───────────▶ Qdrant Vector DB
│ │ RedisCache │───────────▶ Redis Cache
│ └───────────────┘ │
└─────────────────────┘

Step-by-Step: User → DB → User
PHASE 1: INPUT (User to Engine)
You type "Remember: I love Python" in the browser.
Browser sends HTTP POST to /api/memory.
API Router calls interface.py
interface.py calls engine.add_memory("I love Python").
Engine is now in control. The API waits.

PHASE 2: PROCESSING (Inside the Engine "Box")
Engine calls Embedder: "Convert this to a vector."
Engine calls Memory: "Any contradictions? Any similar nodes?"
Engine calls Math: "Calculate the inheritance structure."
Engine decides: "This is a new unique memory."

PHASE 3: SAVING (Engine to Data Layer)
Engine calls store.upsert_node(node).
PostgresStore receives this call.
PostgresStore writes to PostgreSQL database. ✅ Data saved.

PHASE 4: SIGNALING (Engine to Events) ngine calls
emit_node_created(node_id) rom core/events.py.
core/events.py broadcasts this to all subscribers.
api/services/events.py (subscriber) catches it.
api/services/events.py pushes SSE to browser.
Your UI sees the node appear in real-time. ✅ UI updated.

PHASE 5: RESPONSE (Engine to User)
Engine returns node_id to interface.py.
interface.py returns JSON to the API.
API sends HTTP 200 OK to browser.
You see "Memory saved!" message.

                           ┌──────────────────┐
                           │      USER        │
                           │    (Browser)     │
                           └────────┬─────────┘
                                    │ HTTP
                                    ▼

┌───────────────────────────────────────────────────────────────────────────┐
│ API LAYER │
│ Routers ──▶ interface.py ──▶ ENGINE ◀── SSE ◀── api/events.py │
└───────────────────────────────────┬───────────────────────────────────────┘
│
┌───────────────────────────┴─────────────────────────────┐
│ │ │
▼ ▼ ▼
┌───────────────┐ ╔═══════════════════════════════╗ ┌───────────────┐
│ CORE TOOLS │ ║ ENGINE ║ │ EVENTS │
│ (Embedder, │◀───║ (Coordinator, owns store, ║───▶│ (core/events) │
│ Memory, │ ║ owns schedulers) ║ │ emit signals │
│ Math) │ ╚═══════════════════════════════╝ └───────────────┘
└───────────────┘ │ │
│ store.upsert() │ notify UI
▼ ▼
┌─────────────────────────────┐ ┌─────────────────┐
│ DATA LAYER │ │ api/events.py │
│ PostgresStore, RedisCache │ │ (SSE to User) │
└──────────────┬──────────────┘ └─────────────────┘
│
▼
┌─────────────────────────────┐
│ ACTUAL DATABASES │
│ PostgreSQL, Qdrant, Redis │
└─────────────────────────────┘

User uploads "report.pdf"
│
▼
┌─────────────────────────────────────┐
│ EXTRACTOR │
│ (extractors.py) │
│ PDF → Plain Text │
└─────────────────────────────────────┘
│
▼
┌─────────────────────────────────────┐
│ INGEST SERVICE │
│ (ingest_service.py) │
│ Text → Chunks only │ ◀── NO EMBEDDING HERE
│ (Just split into pieces) │
└─────────────────────────────────────┘
│
│ For each chunk:
│ engine.add_memory(chunk)
▼
╔═════════════════════════════════════╗
║ ENGINE (THE BOSS) ║
║ ┌─────────────┐ ║
║ │ Embedder │ ◀── Embedding ║
║ │ Memory │ happens HERE ║
║ │ Store │ ║
║ └─────────────┘ ║
╚═════════════════════════════════════╝
│ │
│ store.upsert() │ emit_node_created()
▼ ▼
┌──────────────┐ ┌───────────────┐
│ DATA LAYER │ │ EVENTS │
│ Postgres │ │ SSE → User │
│ Qdrant │ │ (Real-time) │
└──────────────┘ └───────────────┘

What Changes in
ingest_service.py
BEFORE (Current - Bypasses Engine):

python

# BAD: Direct embedding and storage

embedder = get_embedder()
vectors = embedder.embed_batch(chunk_texts)
vector_store = get_qdrant_store(...)
\_store_node_postgres(...) # Direct DB access
AFTER (Your Design - Engine is King):

python

# GOOD: Let Engine handle everything

from faim.api.adapters.interface import \_get_engine
engine = \_get_engine()
for chunk in chunks:
engine.add_memory(graph_id, chunk) # Engine does embed + store + events
