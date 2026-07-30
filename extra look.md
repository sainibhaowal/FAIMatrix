NOW ADD CLAISFIED  AUTO CLASIDIED BUTTON.-----1. WHY 4 BUTTONS IF CORTEX AUTO-CLASSIFIES?
Two different things working together:

Layer	What It Does	User Control
Answer Mode (4 buttons)	direct, timeline, contradiction, provenance — Controls HOW the answer is synthesized and presented	User selects — shown in UI at @/frontend/src/components/memoryquery/ChatComposer.tsx:107
Task Type (auto-classified)	answer, timeline, contradiction, provenance, compare, predict, investigate, consolidate, ask_follow_up — What cognitive mode Cortex uses internally	Cortex decides based on keywords----------- CHECK IS THAT STILL I HAVE THESE LIMITATION --Current Limitations
1. Writeback is Proposals Only
Phase 1 safety rule (@/faim_native/Docs/67_FAIM_CORTEX_RUNTIME_ARCHITECTURE.md:47):

"Do not write memory automatically in Phase 1"

Writeback candidates are stored but not automatically executed. Requires manual approval or future policy automation.

2. No Raw Chain-of-Thought Storage
Safety rule (@/faim_native/Docs/67_FAIM_CORTEX_RUNTIME_ARCHITECTURE.md:46):

"Do not store raw chain-of-thought"

Only structured reasoning is persisted. The "thinking" is typed, not free-form.

3. Classification is Keyword-Based
Not semantic understanding — just keyword matching (@/faim_native/core/cortex/planner.py). Can miss nuanced intent.

4. Single-Tenant Graph Scope
Each session is bound to one graph_id. No cross-graph reasoning in Phase 1.

5. Limited Context Window
Only last 6 turns loaded for continuity (@/faim_native/core/cortex/history.py:24). Older session history is accessible via API but not injected into current turn context.--- ALSO CHECK--DID WE HAVE ALREDAY UPDATED LANDING PAGE--AS YOUSAID   What Makes It Powerful
1. Deterministic Structured Reasoning
No black-box chain-of-thought
Every reasoning step is typed, bounded, and auditable
Branch outputs are explicit, not hidden
2. Self-Aware Memory System
Knows what's missing (open_questions)
Knows what's conflicting (contradictions)
Knows what to do next (next_actions)
Proposes memory updates (writeback_candidates)
3. Session Continuity
Maintains conversation context across turns
Tracks unresolved threads
Session summary evolves with each turn
4. Provenance & Auditability
Every answer traces back to source documents
File names, page numbers, block IDs preserved
SHA-256 integrity on all data
5. No ML in Core
Pure deterministic algorithms
Keyword classification (not neural)
Vector similarity (not embeddings)
Rule-based prediction (not trained models)---DID WE HAVE ALREDAY UPDATED OR NOT ??--- WHAT YOU MEAN OF THIS --Not creative — won't generate novel insights beyond evidence
Keyword-rigid — classification can be brittle
Manual writeback — doesn't learn automatically yet
Limited context — 6-turn continuity window EXPLAIN ME THESE---   

-- ALSO --CAN YOU EXPLAIN ME WHAT IS YOUR FUTURE SCOPE REGARDING THIS FAIM--WHERE I CAN SEE MY FAIM IN FUTURE? --WHAT KIND OF UPDATE YOU WILL BRING ?? --WHAT YOU THIN K WHAT FAIM SHOULD HAVE IN FUTURE ?? --IS THIS REALY USEFULL FOR STUDENT, TEACHER, COMPANIES, OR IN GENERAL??--HOW YOU SEE THIS IN 5 YEAR ? --WHAT SHOULD I DO FOR THIS FAIM GOING TO BE LIKE ChatGPT? --IF YES ? THEN HOW?? -- IF NOT THEN WHY ?? -- IS THIS REALM FAIM GOOD OR NOT ??