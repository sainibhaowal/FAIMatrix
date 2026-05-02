#!/bin/bash
# FAIM-Native: Background Zero-Waste Cleanup Guard
# Purpose: Silently cleans up dead Docker images and containers to keep storage at 100% efficiency.
docker system prune -af > /dev/null 2>&1
