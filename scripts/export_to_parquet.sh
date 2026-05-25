#!/bin/bash
# Export Cassandra to Parquet
# Standalone on-demand export script

set -e

# Get project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Parse arguments
OUTPUT_DIR="${1:-./data/parquet}"
CHUNK_SIZE="${2:-400}"

echo "=========================================="
echo "Export Cassandra → Parquet"
echo "=========================================="
echo "Output directory: $OUTPUT_DIR"
echo "Chunk size: $CHUNK_SIZE rows/file"
echo ""

# Run Python script
python scripts/export_to_parquet.py \
    --output-dir "$OUTPUT_DIR" \
    --chunk-size "$CHUNK_SIZE"

echo "✓ Export completed"
