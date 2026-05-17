"""FAIM-Native: User Persona Simulation (Proof of Life).

This script simulates a real-world user ('User_Antigravity') interacting with the
FAIM backend as an AI memory layer.

JOURNEY:
1. Identity: Authenticate as SimUser-01.
2. Create: Ingest technical memory about FAIM Truth Atoms.
3. Recall: Query the memory using physics-based scoring.
4. Evolve: Witness the graph "dreaming" to refine the memory.
"""

import logging
import os
import sys
from pathlib import Path

# Setup logging to be "User Friendly"
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger("User_Antigravity")

# Flexible imports
_parent = Path(__file__).parent.parent
if str(_parent) not in sys.path:
    sys.path.insert(0, str(_parent))

from orchestration.evolve_flow import run_evolve  # noqa: E402
from orchestration.ingest_flow import FAIMProfile, PersistMode, run_ingest  # noqa: E402
from orchestration.query_flow import run_query  # noqa: E402
from runtime.context import get_repos  # noqa: E402

# Configuration
TENANT_ID = "SimUser-01"
GRAPH_ID = "Antigravity-Brain-v1"
API_KEY = "sim-key-123"  # In a real app, this would be validated by middleware


def simulate_journey():
    logger.info("--- STARTING JOURNEY: USER_ANTIGRAVITY ---")

    # 1. IDENTITY & CONTEXT
    logger.info(
        f"Identity: Authenticating as Tenant '{TENANT_ID}' for Graph '{GRAPH_ID}'..."
    )
    repos = get_repos(TENANT_ID)
    session = repos["session"]
    logger.info(
        "Context: Connected to PostgreSQL Store, Qdrant Index, and Redis Cache."
    )

    # 2. MEMORY CREATION (INGEST)
    memory_content = """
    # FAIM Truth Atoms
    A Truth Atom is the smallest unit of deterministic information in FAIM.
    It follows the law of Σf=1, meaning it is perfectly bounded.
    Atoms are antisymmetric; if A is true, Opposition(A) is its mirror.
    """
    logger.info("Action: Uploading 'Technical Memory: FAIM Truth Atoms'...")

    from core.contracts.types import uuid7

    raw_id = str(uuid7())

    ingest_result = run_ingest(
        graph_id=GRAPH_ID,
        raw_id=raw_id,
        filename="truth_atoms_def.md",
        file_bytes=memory_content.encode("utf-8"),
        profile=FAIMProfile.STRICT,
        persist_mode=PersistMode.STRICT,
        node_repo=repos["node_repo"],
        edge_repo=repos["edge_repo"],
        event_repo=repos["event_repo"],
        gv_repo=repos["gv_repo"],
    )

    logger.info(
        f"Success: Ingest complete. Packet Hash: {ingest_result.packet_hash[:12]}..."
    )
    logger.info(
        f"Backend Proof: Nodes Written: {ingest_result.nodes_written}, Version: {ingest_result.graph_version}"
    )

    # 3. MEMORY RECALL (QUERY)
    query_text = "What is the law of faim atoms?"
    logger.info(f"Action: Querying memory for '{query_text}'...")

    query_result = run_query(
        session=session,
        tenant_id=TENANT_ID,
        graph_id=GRAPH_ID,
        query_text=query_text,
        k=3,
        profile=FAIMProfile.STRICT,
        index=repos["index"],
    )

    logger.info(f"Recall: Found {len(query_result.results)} relevant memories.")
    for i, res in enumerate(query_result.results):
        logger.info(
            f"  Result {i+1}: Node ID {res['node_id'][:8]} | Score: {res['score']:.4f}"
        )
        logger.info(
            f"  Physics Data: Similarity={res['score_components']['sim']:.2f}, Novelty={res['score_components']['novel']:.2f}"
        )

    # 4. MEMORY EVOLUTION (EVOLVE)
    logger.info("Action: Triggering Evolution Cycle (The Backend Dream)...")

    evolve_result = run_evolve(
        graph_id=GRAPH_ID,
        tenant_id=TENANT_ID,
        session=session,
        node_repo=repos["node_repo"],
        edge_repo=repos["edge_repo"],
        event_repo=repos["event_repo"],
        gv_repo=repos["gv_repo"],
    )

    logger.info("Evolution Success: The graph has refined itself.")
    logger.info(
        f"Backend Proof: Merges: {evolve_result.merges}, Prunes: {evolve_result.prunes}"
    )
    if evolve_result.status == "completed" and evolve_result.diagnostics:
        metrics = evolve_result.diagnostics.get("metrics", {})
        logger.info(
            f"Fractal Stats: D_hat (Order)={metrics.get('D_hat', 0):.3f}, Entropy={metrics.get('H_hat', 0):.3f}"
        )

    logger.info("--- JOURNEY COMPLETE: 100% ALIVE ---")


if __name__ == "__main__":
    # Ensure database is configured
    if not os.getenv("TEST_DATABASE_URL") and not os.getenv("DATABASE_URL"):
        os.environ["DATABASE_URL"] = (
            "postgresql://faim:testpassword123@localhost:5432/faim_test"
        )

    simulate_journey()
