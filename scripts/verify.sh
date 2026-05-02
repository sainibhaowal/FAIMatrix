#!/bin/bash
# verify.sh - Run all FAIM-Native tests (Store, Perception, Encoding, Core)
#
# Usage:
#   cd /home/sephi-asi/FAIM/faim/Faim_Native
#   ./scripts/verify.sh
#
# Exit codes:
#   0 - All tests passed
#   1 - Some tests failed

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FAIM_NATIVE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "============================================"
echo "FAIM-Native Full Test Suite"
echo "============================================"
echo ""
echo "Faim_Native root: $FAIM_NATIVE_ROOT"
echo ""

# Change to Faim_Native directory to isolate from parent faim package
cd "$FAIM_NATIVE_ROOT"

# Set PYTHONPATH to Faim_Native only (exclude parent faim package)
export PYTHONPATH="$FAIM_NATIVE_ROOT"

echo "Running tests..."
echo ""

# Run pytest with local pytest.ini config
python3 -m pytest tests/ \
    -v \
    --tb=short \
    -c pytest.ini \
    "$@"

echo ""
echo "============================================"
echo "✓ All tests passed!"
echo "============================================"
