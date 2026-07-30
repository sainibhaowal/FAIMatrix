#!/usr/bin/env python3
"""Extract blocks from a raw file and create a MemoryPacket.

Usage:
    python scripts/extract_packet.py <raw_id> [--file /path/to/file] [--output packet.json]

Examples:
    # Extract from blob store by raw_id
    python scripts/extract_packet.py abc123def456

    # Extract directly from file
    python scripts/extract_packet.py my_raw_id --file /path/to/document.pdf --output output.json
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
from perception.packetize import create_packet, packet_to_json  # noqa: E402
from perception.router import route_extraction  # noqa: E402
from perception.validate import validate_all  # noqa: E402


def main():
    parser = argparse.ArgumentParser(
        description="Extract blocks and create MemoryPacket"
    )
    parser.add_argument("raw_id", help="Raw reference ID")
    parser.add_argument("--file", "-f", help="Path to file (if not using blob store)")
    parser.add_argument("--output", "-o", help="Output JSON file (default: stdout)")
    parser.add_argument(
        "--validate", "-v", action="store_true", help="Validate packet before output"
    )
    args = parser.parse_args()

    # Load file content
    if args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"Error: File not found: {args.file}", file=sys.stderr)
            sys.exit(1)

        file_bytes = file_path.read_bytes()
        filename = file_path.name
    else:
        # Would load from blob store here
        print(
            "Error: --file is required (blob store lookup not implemented)",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Extracting blocks from: {filename}", file=sys.stderr)
    print(f"Raw ID: {args.raw_id}", file=sys.stderr)

    # Extract blocks
    blocks = route_extraction(file_bytes, filename, args.raw_id)
    print(f"Extracted {len(blocks)} blocks", file=sys.stderr)

    # Sort blocks
    sorted_blocks = sort_blocks(blocks)

    # Create packet
    packet = create_packet(args.raw_id, sorted_blocks)
    print(f"Created packet: {packet.id}", file=sys.stderr)
    print(f"Packet hash: {packet.packet_hash}", file=sys.stderr)

    # Validate if requested
    if args.validate:
        errors = validate_all(packet, sorted_blocks)
        if errors:
            print(f"\nValidation errors ({len(errors)}):", file=sys.stderr)
            for error in errors:
                print(f"  - {error}", file=sys.stderr)
            sys.exit(1)
        else:
            print("Validation: PASSED", file=sys.stderr)

    # Output JSON
    output = packet_to_json(packet, sorted_blocks)
    json_str = json.dumps(output, indent=2)

    if args.output:
        Path(args.output).write_text(json_str)
        print(f"Wrote packet to: {args.output}", file=sys.stderr)
    else:
        print(json_str)


if __name__ == "__main__":
    main()
