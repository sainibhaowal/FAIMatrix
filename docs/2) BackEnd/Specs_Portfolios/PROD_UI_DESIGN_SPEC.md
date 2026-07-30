# FAIM-Native: Production UI Design Specification

This document defines the professional, production-ready interface for FAIM-Native. It moves beyond "dashboards" into a multi-workspace **Cognitive Operating System**.

---

## 🏗️ 1. GLOBAL APPLICATION LAYOUT
The app uses a "Golden Ratio" layout designed for heavy data density and intuitive navigation.

### **A. Top Navigation Bar (The Context Bar)**
- **Logo**: FAIM-Native (Home)
- **Tenant Switcher**: A searchable dropdown that allows admins to switch between `Organizations` and `Tenants`.
- **Global Search**: "Command + K" style bar for fast retrieval across all graphs.
- **System Pulse**: Real-time status indicator (Connected, Latency, API Version).
- **User Profile**: Avatar, User ID, and Logout.

### **B. Sidebar (The Workspaces)**
- **🏠 Dashboard**: High-level health and entropy metrics.
- **🕸️ Graph Explorer**: The central neural map and node interaction space.
- **📥 Ingest Station**: Drag-and-drop intake for raw documents and data streams.
- **⚙️ Evolution Lab**: Live view of "Sleep Cycle" merges and memory pruning.
- **🔐 Security & Keys**: API Key management, Tenant provisioning, and Hashing settings.

---

## 🔐 2. SECURITY & SETTINGS WORKSPACE
This is where developers manage the "Shield" we built.

### **API Key Management**
- **Table View**: Displays Key Name, Masked Key (`faim_...xxxx`), Created At.
- **Create New Key**: Button that displays the plaintext key **only once** (Security first).
- **Revoke**: Nuclear option for compromised keys.

### **Storage Monitor**
- **Postgres Usage**: Total rows, table size, and growth trends.
- **Vector Space**: Qdrant collection density and shard health.
- **Redis Cache**: Hit/Miss ratios and TTL counts.

---

## 🧬 3. THE GRAPH EXPLORER (The Brain)
The core visual experience of FAIM-Native.

### **The Neural Graph**
- Nodes are color-coded by **Influence** (High Influence nodes glow brighter).
- Edges represent **Inheritance** and **Similarity**.
- Real-time updates: When a node is merged or pruned, the graph reflects the change with a bio-purple particle animation.

### **Node Inspector (Side Panel)**
When a user clicks a node, a detailed panel slides out:
- **UUID**: The native UUID7 identifier.
- **Content Snippet**: Pre-rendered markdown of the evidence block.
- **Physics Metadata**: Entropy value, Influence weight, and Checksum.
- **Lineage**: Links to Parent and Child memory fragments.

---

## 🔌 4. BACKEND-TO-UI MAPPING (Production Guide)

| UI Component | Backend Router | Essential Payload Items |
| :--- | :--- | :--- |
| **Tenant Switcher** | `auth.py` | `organizations`, `tenants` |
| **API Key Table** | `auth_repo.py` | `key_id`, `created_at`, `revoked_at` |
| **Graph View** | `node.py`, `query.py` | `nodes`, `edges`, `faim_vector` |
| **SSE Activity** | `events.py` | `NODE_CREATED`, `BLOCK_MERGED` |
| **Resource Meter** | `metrics.py` | `db_size`, `memory_usage` |

---

## 🏁 FINAL SUMMARY
This design ensures that your users feel they are interacting with a **Sophisticated Intelligence Structure**, not just a database. It prioritizes **Visibility, Context, and Security**.
