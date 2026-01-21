#!/bin/bash
# =============================================================================
# FAIM-Native: Zero-Waste Update Script
# =============================================================================
# This script ensures that Docker only keeps ACTIVE images and containers.
# Every execution pulls/builds the latest version and prunes the "dead" weight.
# =============================================================================

set -e

echo "🚀 Starting FAIM-Native Zero-Waste Update..."

# 1. Build/Update the stack
echo "📦 Building/Pulling latest images..."
docker compose build --pull

# 2. Restart services
echo "🔄 Rolling out updates..."
docker compose up -d

# 3. ENFORCE ZERO-WASTE POLICY
# This command deletes all stopped containers, unused networks, and dangling/dead images.
echo "🧹 Executing Zero-Waste Prune..."
docker system prune -af

echo "✅ FAIM Update Complete. Storage is 100% Lean."
docker images faim-native:latest
