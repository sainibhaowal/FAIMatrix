"""Backfill cognitive type and galaxy_id for existing nodes."""

import sys
from collections import Counter
from pathlib import Path

# Setup path for local execution
root = Path(__file__).parent.parent.parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from core.cognitive.cognitive_typing import (  # noqa: E402
    CognitiveType,
    classify_cognitive_type,
    extract_galaxy_title,
    generate_galaxy_id,
)
from sqlalchemy import text  # noqa: E402

from store.pg.session import get_session  # noqa: E402


def backfill_nodes(batch_size: int = 100):
    """Backfill cognitive_type and galaxy_id for all nodes without them."""
    session = get_session()

    # Get count of nodes needing backfill
    result = session.execute(
        text(
            "SELECT COUNT(*) FROM nodes WHERE cognitive_type IS NULL OR cognitive_type = ''"
        )
    )
    total = result.scalar()
    print(f"Nodes needing backfill: {total}")

    if total == 0:
        print("No nodes to backfill.")
        return

    # Process in batches
    updated = 0

    while True:
        # Get batch of nodes
        result = session.execute(text("""
            SELECT node_id, raw_id, anchor_json, kind
            FROM nodes
            WHERE cognitive_type IS NULL OR cognitive_type = ''
            LIMIT :batch_size
        """).params(batch_size=batch_size))

        rows = result.fetchall()
        if not rows:
            break

        for row in rows:
            node_id, raw_id, anchor_json, kind = row

            # 1. Galaxy ID
            galaxy_title = extract_galaxy_title(raw_id or "unknown")
            galaxy_id = generate_galaxy_id(raw_id or str(node_id), galaxy_title)

            # 2. Cognitive Type
            cog_type = None

            if kind == "macro":
                # Vote on cognitive type from inheritance parent (member) nodes.
                # This mirrors the same Counter.most_common logic in invention_native.py.
                try:
                    member_result = session.execute(text("""
                        SELECT n.cognitive_type
                        FROM edges e
                        JOIN nodes n ON n.node_id = e.src_node_id
                        WHERE e.dst_node_id = :node_id
                          AND e.kind = 'inheritance'
                          AND n.cognitive_type IS NOT NULL
                          AND n.cognitive_type != ''
                    """).params(node_id=node_id))
                    member_types = [row[0] for row in member_result.fetchall()]
                    if member_types:
                        cog_type = Counter(member_types).most_common(1)[0][0]
                    else:
                        # Members not yet classified — default to FACT
                        cog_type = CognitiveType.FACT.value
                except Exception:
                    # Safe fallback — never abort the backfill on a query error
                    cog_type = CognitiveType.FACT.value
            else:
                # Use classify_cognitive_type for atoms
                text_content = ""
                if isinstance(anchor_json, dict):
                    text_content = anchor_json.get("text", "") or anchor_json.get(
                        "canonical", ""
                    )

                context = {"source_type": "document"}
                if raw_id:
                    rid_lower = raw_id.lower()
                    if "meeting" in rid_lower or "call" in rid_lower:
                        context["has_timestamp"] = True

                cog_type = classify_cognitive_type(text_content, context).value

            # Update the node
            session.execute(text("""
                UPDATE nodes
                SET cognitive_type = :cog_type, galaxy_id = :galaxy_id
                WHERE node_id = :node_id
            """).params(cog_type=cog_type, galaxy_id=galaxy_id, node_id=node_id))

            updated += 1

        session.commit()
        print(f"Updated {updated}/{total} nodes...")

    print(f"Backfill complete! Updated {updated} nodes.")


if __name__ == "__main__":
    backfill_nodes()
