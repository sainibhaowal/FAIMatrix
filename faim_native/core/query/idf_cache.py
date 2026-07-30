"""IDF Weight Cache — Compute and apply inverse document frequency weighting.

Phase 3C: Query-time IDF weighting to down-weight common n-gram buckets
and up-weight rare ones.

Theory:
  IDF[i] = log(N / (DF[i] + 1))
  where:
    N = total number of nodes in the graph
    DF[i] = document frequency (count of nodes with nonzero value in bucket i)

Application:
  weighted_q_vec[i] = q_vec[i] * IDF[i]
  Then re-normalize the weighted query vector.

Benefits:
  - Down-weights common n-grams (e.g., "the", "is")
  - Up-weights rare/specific n-grams (e.g., "fractal", "inheritance")
  - Applied only to query vector (stored vectors unchanged) → no re-ingest required
"""

import math
from typing import List, Tuple


def compute_idf_weights(
    session,
    tenant_id: str,
    graph_id: str,
    dimension: int = 256,
) -> List[float]:
    """
    Compute IDF weights from all stored node vectors for the given graph.

    Loads all v_native vectors and counts document frequency per bucket.

    Args:
        session: SQLAlchemy session.
        tenant_id: Tenant ID.
        graph_id: Graph ID.
        dimension: Vector dimension (default 256).

    Returns:
        List of `dimension` IDF floats.
    """
    from store.pg.models_faim import NodeModel

    nodes = (
        session.query(NodeModel.v_native)
        .filter(
            NodeModel.tenant_id == tenant_id,
            NodeModel.graph_id == graph_id,
        )
        .all()
    )

    N = len(nodes)
    if N == 0:
        return [1.0] * dimension

    # Count document frequency per bucket
    df = [0] * dimension
    for (v_native,) in nodes:
        for i, val in enumerate(v_native[:dimension]):
            if val != 0.0:
                df[i] += 1

    # Compute IDF: log(N / (DF[i] + 1)) + 1.0
    # Adding 1.0 ensures all IDF values are > 0, avoiding zeroing out query buckets
    idf = [math.log(N / (df[i] + 1)) + 1.0 for i in range(dimension)]
    return idf


def apply_idf(q_vec: Tuple[float, ...], idf: List[float]) -> Tuple[float, ...]:
    """
    Apply IDF weighting to query vector and re-normalize.

    Args:
        q_vec: Query vector (tuple of floats).
        idf: IDF weights (list of floats, same dimension as q_vec).

    Returns:
        IDF-weighted and re-normalized query vector (tuple of floats).
    """
    # Element-wise multiply
    weighted = tuple(q_vec[i] * idf[i] for i in range(len(q_vec)))

    # Re-normalize (L2)
    norm = math.sqrt(sum(x * x for x in weighted)) or 1.0
    return tuple(x / norm for x in weighted)
