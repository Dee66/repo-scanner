#!/bin/bash
# Repository Intelligence Scanner - Build Script
# Builds Docker images for enterprise deployment

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "🏗️  Building Repository Intelligence Scanner..."

# Build the production image
docker build -t repo-scanner:latest .

# Tag with version if provided
if [ -n "$1" ]; then
    docker tag repo-scanner:latest "repo-scanner:$1"
    echo "✅ Tagged as repo-scanner:$1"
fi

echo "✅ Build complete!"
echo ""
echo "📋 Available images:"
docker images repo-scanner