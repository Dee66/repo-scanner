#!/bin/bash
# Repository Intelligence Scanner - Deployment Script
# Deploys the scanner using Docker Compose

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Default values
REPO_PATH="${REPO_PATH:-$PROJECT_ROOT}"
OUTPUT_DIR="${OUTPUT_DIR:-$PROJECT_ROOT/reports}"
MODEL_CACHE="${MODEL_CACHE:-$PROJECT_ROOT/models}"
LOG_LEVEL="${LOG_LEVEL:-INFO}"
MAX_WORKERS="${MAX_WORKERS:-4}"

echo "🚀 Deploying Repository Intelligence Scanner..."
echo "📁 Repository Path: $REPO_PATH"
echo "📊 Output Directory: $OUTPUT_DIR"
echo "🤖 Model Cache: $MODEL_CACHE"
echo "📝 Log Level: $LOG_LEVEL"
echo "⚡ Max Workers: $MAX_WORKERS"
echo ""

# Create necessary directories
mkdir -p "$OUTPUT_DIR" "$MODEL_CACHE"

# Export environment variables for docker-compose
export REPO_PATH OUTPUT_DIR MODEL_CACHE LOG_LEVEL MAX_WORKERS

# Build and start services
if [ "$1" = "api" ]; then
    echo "🌐 Starting with API server..."
    docker-compose --profile api up --build -d
elif [ "$1" = "worker" ]; then
    echo "⚙️  Starting worker mode..."
    docker-compose --profile worker up --build -d
else
    echo "🔍 Starting scanner..."
    docker-compose up --build -d
fi

echo "✅ Deployment complete!"
echo ""
echo "📋 Running containers:"
docker ps --filter "name=repo-scanner"

echo ""
echo "📊 To view logs:"
echo "  docker-compose logs -f"
echo ""
echo "🛑 To stop:"
echo "  docker-compose down"