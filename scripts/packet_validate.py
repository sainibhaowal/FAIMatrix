#!/usr/bin/env python3
"""Validate a MemoryPacket JSON file.

Usage:
    python scripts/packet_validate.py <packet.json>

Examples:
    python scripts/packet_validate.py output.json

Exit codes:
    0 - Validation passed
    1 - Validation failed
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

from perception.packetize import packet_from_json  # noqa: E402
from perception.validate import validate_blocks, validate_packet  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Validate a MemoryPacket JSON file")
    parser.add_argument("packet_file", help="Path to packet JSON file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    # Load packet file
    file_path = Path(args.packet_file)
    if not file_path.exists():
        print(f"Error: File not found: {args.packet_file}", file=sys.stderr)
        sys.exit(1)

    try:
        data = json.loads(file_path.read_text())
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Validating: {args.packet_file}")

    # Parse packet and blocks
    try:
        packet, blocks = packet_from_json(data)
    except (KeyError, ValueError) as e:
        print(f"Error: Failed to parse packet: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Packet ID: {packet.id}")
    print(f"Raw ID: {packet.raw_id}")
    print(f"Block count: {packet.block_count}")
    print(f"Packet hash: {packet.packet_hash}")

    if args.verbose:
        print("\nBlocks:")
        for i, block in enumerate(blocks):
            print(f"  [{i+1}] {block.block_type}: {block.content[:50]}...")

    # Run validation
    print("\n--- Validation ---")

    block_errors = validate_blocks(blocks)
    packet_errors = validate_packet(packet, blocks)
    all_errors = block_errors + packet_errors

    if block_errors:
        print(f"\nBlock validation errors ({len(block_errors)}):")
        for error in block_errors:
            print(f"  ✗ {error}")
    else:
        print("✓ Block validation: PASSED")

    if packet_errors:
        print(f"\nPacket validation errors ({len(packet_errors)}):")
        for error in packet_errors:
            print(f"  ✗ {error}")
    else:
        print("✓ Packet validation: PASSED")

    # Summary
    print("\n--- Summary ---")
    if all_errors:
        print(f"FAILED with {len(all_errors)} errors")
        sys.exit(1)
    else:
        print("ALL VALIDATIONS PASSED ✓")
        sys.exit(0)


if __name__ == "__main__":
    main()
