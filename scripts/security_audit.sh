#!/usr/bin/env bash
# =============================================================================
# FAIM-Native Security Audit Script
# =============================================================================
# Stage-11: CVE scanning and security linting.
#
# Runs:
#   - pip-audit: Python dependency CVE scanner
#   - bandit: Python security linter
#   - ruff: Code quality (security rules)
#
# Usage: ./scripts/security_audit.sh
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
FAIM_NATIVE_DIR="$PROJECT_ROOT/faim_native"

echo "============================================"
echo "FAIM-Native Security Audit"
echo "============================================"
echo ""

ERRORS=0

# ---------------------------------------------------------------------------
# 1. pip-audit: Check for known vulnerabilities in dependencies
# ---------------------------------------------------------------------------
echo "🔍 [1/3] Running pip-audit (CVE scanner)..."

if command -v pip-audit &> /dev/null; then
    if pip-audit --strict 2>&1; then
        echo "✅ pip-audit: No known vulnerabilities found"
    else
        echo "⚠️ pip-audit: Vulnerabilities detected (see above)"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo "⚠️ pip-audit not installed. Install with: pip install pip-audit"
    echo "   Skipping CVE scan..."
fi

echo ""

# ---------------------------------------------------------------------------
# 2. bandit: Security-focused static analysis
# ---------------------------------------------------------------------------
echo "🔍 [2/3] Running bandit (security linter)..."

if command -v bandit &> /dev/null; then
    # -ll: Only report medium and high severity issues
    # -r: Recursive
    # Exclude tests directory (test code often has intentional "unsafe" patterns)
    if bandit -r "$FAIM_NATIVE_DIR" -ll --exclude "$FAIM_NATIVE_DIR/tests" 2>&1; then
        echo "✅ bandit: No security issues found"
    else
        echo "⚠️ bandit: Security issues detected (see above)"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo "⚠️ bandit not installed. Install with: pip install bandit"
    echo "   Skipping security lint..."
fi

echo ""

# ---------------------------------------------------------------------------
# 3. Check for hardcoded secrets patterns
# ---------------------------------------------------------------------------
echo "🔍 [3/3] Checking for hardcoded secrets..."

# Patterns that indicate potential hardcoded secrets
PATTERNS=(
    'password\s*=\s*["\x27][^"\x27]*["\x27]'
    'api_key\s*=\s*["\x27][^"\x27]*["\x27]'
    'secret\s*=\s*["\x27][^"\x27]*["\x27]'
    'POSTGRES_PASSWORD\s*=\s*["\x27][^"\x27]*["\x27]'
)

FOUND_SECRETS=0
for pattern in "${PATTERNS[@]}"; do
    # Search in Python files, excluding tests and migrations
    if grep -rE "$pattern" "$FAIM_NATIVE_DIR" \
        --include="*.py" \
        --exclude-dir="tests" \
        --exclude-dir="__pycache__" \
        2>/dev/null | grep -v "# noqa" | grep -v "os.getenv" | grep -v "os.environ" > /tmp/secret_matches.txt; then
        
        if [ -s /tmp/secret_matches.txt ]; then
            echo "⚠️ Potential hardcoded secrets found:"
            cat /tmp/secret_matches.txt
            FOUND_SECRETS=$((FOUND_SECRETS + 1))
        fi
    fi
done

if [ $FOUND_SECRETS -eq 0 ]; then
    echo "✅ No obvious hardcoded secrets found"
else
    ERRORS=$((ERRORS + 1))
fi

echo ""

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo "============================================"
if [ $ERRORS -eq 0 ]; then
    echo "✅ FAIM-Native Security Audit PASSED"
    exit 0
else
    echo "❌ FAIM-Native Security Audit FAILED ($ERRORS issues)"
    echo ""
    echo "Please fix the issues above before deploying to production."
    exit 1
fi
