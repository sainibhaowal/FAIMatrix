# 82. FAIM Interactive Cortex & FIG View User Guide

This guide describes the complete interactive lifecycle of a user query in FAIM. It walks through **exactly what happens** behind the scenes (in the Postgres database and Cortex AI brain) and **exactly what you see on the screen** (in the chat interface and the 3D FIG View Knowledge Graph) under different scenarios.

---

## Scenario A: The Standard Search & grounding
*You ask a factual question about stable information.*

### 1. What You Input
You open the FAIM dashboard, select **"Direct Mode"** (or Strict Profile), and type into the chat input:
> *"What is the main component of our rocket engine propellant?"*

### 2. What Happens in the Brain & Database (Cortex Engine)
1. **Recall**: Cortex parses the text, extracts search terms, and queries the vector database for the top matches.
2. **IWQE (Query Expansion)**:
   * The database finds seed node: `Node #101: "RP-1 kerosene propellant used in rocket nozzle system."`
   * IWQE looks up taxonomic `inheritance` parents: `Node #42: "Hydrocarbon fuels"`.
   * The original vector is enriched with the `"Hydrocarbon"` vector component so it finds related facts like `Node #102: "Liquid oxygen oxidizer"`.
3. **Synthesis**: The Cortex Planner classifies this as an `answer` task type and synthesizes a direct response.

### 3. What You See in the FIG View 3D UI
* **Real-time Pulse**: The 3D canvas instantly rotates and glides to focus on the active cluster.
* **Highlighted Node Trails**: Node `#101` and Node `#102` light up in a **vibrant teal glow**.
* **Particle Flow**: Animated glowing particles travel along the inheritance lines connecting Node `#101` $\to$ Node `#42`, visually tracing how the search expanded.

### 4. What You See in the Chat Card
* A clean response appears: *"The rocket engine propellant mainly consists of RP-1 kerosene blended with liquid oxygen."*
* A source drawer opens, showing the source documents with a green badge: `Grounding Confidence: 96%`.

---

## Scenario B: The Contradiction & Temporal Update
*You ask a question about information that has changed over time.*

### 1. What You Input
You select **"Contradiction Mode"** (or Relaxed Profile) and ask:
> *"Who is the current project manager for Project Sirius?"*

### 2. What Happens in the Brain & Database (Cortex Engine)
1. **Retrieve Conflict**: Vector search recalls two conflicting facts:
   * `Node #201`: *"Alice is the Project Manager of Sirius."* (Timestamp: Jan 10th)
   * `Node #202`: *"Bob appointed as new Project Manager of Sirius replacing Alice."* (Timestamp: May 12th)
2. **TCT (Transitive Contradiction Traversal)**:
   * The query engine detects an `opposition` edge between Node `#201` and Node `#202`.
   * It compares timestamps and resolves the conflict:
     * Node `#202` is marked as **CURRENT** (active).
     * Node `#201` is marked as **HISTORICAL** (superseded).
3. **Cortex State Reduction**: The Cortex Planner reduces this state, generating an answer that highlights the correction.

### 3. What You See in the FIG View 3D UI
* **Dual Highlight**: Both nodes glow, but their visual styling is completely distinct:
  * **Node #202 (Bob)**: Glows in a **highly-saturated teal pulsing ring**.
  * **Node #201 (Alice)**: Instantly **dims out into a semi-translucent, amber-orange color**, with a dashed connecting line showing the active supersede pointer going to Node `#202`.

### 4. What You See in the Chat Card
* The response reads: *"Bob is the current Project Manager for Project Sirius. He replaced Alice on May 12th."*
* In the memory trace drawer:
  * `Bob's appointment` shows up as **Current**.
  * `Alice's appointment` shows up with a **strike-through line** (~~Alice is PM~~) labeled **"Historical"** in amber.
  * Hovering over Alice's card displays: `Superseded by Bob's appointment (Node #202)`.

---

## Scenario C: Adding New Information (Ingestion & Background Evolution)
*You upload a new document that changes facts in real-time.*

### 1. What You Input
You drag and drop a new PDF document into the FAIM file upload panel:
> `sirius_update_final.pdf` containing: *"Project Sirius target release date moved to September 30th due to supply delays."*

### 2. What Happens in the Brain & Database (Cortex Engine)
1. **Ingest Pipeline (Sync)**:
   * The file is parsed into text chunks, vectorized, and written to `storage_files` and `nodes`.
   * An ingest transaction is registered in the database, updating `ingest_dedup` to avoid duplicate processing.
2. **Autonomous Evolution (Async Background)**:
   * A background worker job is enqueued in the `jobs` table: `kind: 'evolve'`.
   * The evolve scheduler runs the **Invention Cycle**: It scans the newly added nodes, detects semantic overlaps with existing nodes (e.g. older Sirius release dates like June 1st), and **creates an `opposition` edge** connecting the old release node to the new September 30th node.

### 3. What You See in the FIG View 3D UI
* **New Cluster Creation**: A new node enters the 3D space, floating towards the "Project Sirius" cluster using physics attraction.
* **Edge Connection**: A line is dynamically drawn between the old release node and the new node.
* **Color Shifting**: The old release node shifts color from **Teal (Current)** to **Amber-Orange (Historical/Superseded)**, representing that the system's memory has updated.

### 4. What You See in the Chat Card
The next time you query about the release date, the chat response immediately returns:
* *"Project Sirius is scheduled to release on September 30th."*
* The trace drawer highlights the new September 30th node as the active ground source, and shows the old June 1st node as superseded.
