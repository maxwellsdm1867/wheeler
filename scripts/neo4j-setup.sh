#!/usr/bin/env bash
# Start Neo4j Community Edition in Docker for Wheeler.
# Usage: bash scripts/neo4j-setup.sh

set -euo pipefail

CONTAINER_NAME="wheeler-neo4j"
NEO4J_IMAGE="neo4j:community"
NEO4J_PASSWORD="${NEO4J_PASSWORD:-research-graph}"
BOLT_PORT="${BOLT_PORT:-7687}"
HTTP_PORT="${HTTP_PORT:-7474}"
DATA_DIR="${DATA_DIR:-$HOME/.wheeler/neo4j-data}"

# Check if Docker is available
if ! command -v docker &>/dev/null; then
    echo "Error: Docker is not installed or not in PATH." >&2
    exit 1
fi

# Stop existing container if running
if docker ps -q -f name="$CONTAINER_NAME" | grep -q .; then
    echo "Stopping existing $CONTAINER_NAME container..."
    docker stop "$CONTAINER_NAME" >/dev/null
fi

# Remove existing container
if docker ps -aq -f name="$CONTAINER_NAME" | grep -q .; then
    echo "Removing existing $CONTAINER_NAME container..."
    docker rm "$CONTAINER_NAME" >/dev/null
fi

# Create data directory
mkdir -p "$DATA_DIR"

echo "Starting Neo4j Community Edition..."
echo "  Bolt:    bolt://localhost:$BOLT_PORT"
echo "  Browser: http://localhost:$HTTP_PORT"
echo "  Data:    $DATA_DIR"

docker run -d \
    --name "$CONTAINER_NAME" \
    -p "$BOLT_PORT:7687" \
    -p "$HTTP_PORT:7474" \
    -v "$DATA_DIR:/data" \
    -e NEO4J_AUTH="neo4j/$NEO4J_PASSWORD" \
    "$NEO4J_IMAGE"

echo ""
echo "Neo4j is starting up. It may take a few seconds to become available."
echo "Initialize the Wheeler schema with: wheeler-tools graph init"
