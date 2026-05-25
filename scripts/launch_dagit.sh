#!/bin/bash
# Launch Dagit UI for arXiv pipeline
# Usage: bash scripts/launch_dagit.sh

set -e

echo "=========================================="
echo "Launching Dagster Dagit UI"
echo "=========================================="
echo ""

# Set environment variables
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
export DAGSTER_HOME="${DAGSTER_HOME:-.dagster}"

# Navigate to project root
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "Project root: $PROJECT_ROOT"
echo "DAGSTER_HOME: $DAGSTER_HOME"
echo ""

# Check if python is installed
if ! command -v python &> /dev/null; then
    echo "ERROR: python not found. Install Python 3.10+"
    exit 1
fi

echo "Starting Dagit..."
echo ""
echo "Dagit UI will be available at:"
echo "   http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Launch Dagit on port 3000 using Python module
python -m dagit -f pipelines/dagster_pipeline.py -p 3000

exit 0
