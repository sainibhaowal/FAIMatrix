#!/usr/bin/env python3
"""Encode atoms from raw file to FAIMVectors.

Full pipeline: raw_id → load bytes → extract blocks → create packet → encode vectors → write JSON

Usage:
    python scripts/encode_atoms.py <raw_id> --file /path/to/file --output vectors.json

Examples:
    python scripts/encode_atoms.py raw_abc123 --file document.pdf --output vectors.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Setup paths
_script_dir = Path(__file__).parent
_faim_native = _script_dir.parent
if str(_faim_native) not in sys.path:
    sys.path.insert(0, str(_faim_native))

from core.contracts.types import sort_blocks  # noqa: E402
from encoding.text_vectorizer import vectorize_blocks  # noqa: E402
from encoding.vector_schema import SCHEMA_VERSION, VECTOR_DIMENSION  # noqa: E402
from perception.packetize import create_packet  # noqa: E402
from perception.router import route_extraction  # noqa: E402
from perception.validate import validate_all  # noqa: E402


def main():
    parser = argparse.ArgumentParser(
        description="Encode atoms from file to FAIMVectors"
    )
    parser.add_argument("raw_id", help="Raw reference ID")
    parser.add_argument("--file", "-f", required=True, help="Path to file")
    parser.add_argument("--output", "-o", required=True, help="Output JSON file")
    parser.add_argument(
        "--validate", "-v", action="store_true", help="Validate packet before encoding"
    )
    args = parser.parse_args()

    # Load file
    file_path = Path(args.file)
    if not file_path.exists():
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        sys.exit(1)

    file_bytes = file_path.read_bytes()
    filename = file_path.name

    print("=== FAIM-Native Encoder ===", file=sys.stderr)
    print(f"File: {filename}", file=sys.stderr)
    print(f"Raw ID: {args.raw_id}", file=sys.stderr)
    print(f"Schema: {SCHEMA_VERSION} (dim={VECTOR_DIMENSION})", file=sys.stderr)

    # Step 1: Extract blocks
    print("\n[1/4] Extracting blocks...", file=sys.stderr)
    blocks = route_extraction(file_bytes, filename, args.raw_id)
    sorted_blocks = sort_blocks(blocks)
    print(f"      Extracted {len(sorted_blocks)} blocks", file=sys.stderr)

    # Step 2: Create packet
    print("[2/4] Creating packet...", file=sys.stderr)
    packet = create_packet(args.raw_id, sorted_blocks)
    print(f"      Packet ID: {packet.id}", file=sys.stderr)
    print(f"      Packet hash: {packet.packet_hash[:16]}...", file=sys.stderr)

    # Step 3: Validate (optional)
    if args.validate:
        print("[3/4] Validating...", file=sys.stderr)
        errors = validate_all(packet, sorted_blocks)
        if errors:
            print(f"      FAILED with {len(errors)} errors:", file=sys.stderr)
            for e in errors[:5]:
                print(f"        - {e}", file=sys.stderr)
            sys.exit(1)
        print("      Validation PASSED", file=sys.stderr)
    else:
        print("[3/4] Skipping validation...", file=sys.stderr)

    # Step 4: Encode vectors
    print("[4/4] Encoding vectors...", file=sys.stderr)
    vectors = vectorize_blocks(sorted_blocks)
    print(f"      Encoded {len(vectors)} vectors", file=sys.stderr)

    # Verify hashes
    for v in vectors:
        if not v.verify_hash():
            print(
                f"      WARNING: Vector hash mismatch for {v.block_id}", file=sys.stderr
            )

    # Build output
    output = {
        "schema_version": SCHEMA_VERSION,
        "raw_id": args.raw_id,
        "packet": packet.to_dict(),
        "vectors": [v.to_dict() for v in vectors],
        "stats": {
            "block_count": len(sorted_blocks),
            "vector_count": len(vectors),
            "dimension": VECTOR_DIMENSION,
        },
    }

    # Write output
    output_path = Path(args.output)
    output_path.write_text(json.dumps(output, indent=2))
    print(f"\n✓ Wrote {len(vectors)} vectors to: {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
