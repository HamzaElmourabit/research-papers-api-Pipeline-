#!/bin/bash
# Run the Databricks Spark pipeline in Docker using Apache Spark 3.4.1.
# Requires Docker Compose services (zookeeper, kafka, cassandra) to be up.

set -e

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
WORKSPACE="$ROOT_DIR"
DATA_DIR="$ROOT_DIR/data"
NETWORK_NAME="researchpapersapi-copy_arxiv_network"
SPARK_IMAGE="apache/spark:3.4.1"
IVY_CACHE="/tmp/.ivy2"

echo "Starting Databricks Spark pipeline in Docker..."

docker ps >/dev/null 2>&1 || {
  echo "❌ Docker daemon is not responding. Start Docker Desktop first."
  exit 1
}

echo "Using Spark image: $SPARK_IMAGE"

# Create Docker named volume for data (if not exists)
echo "Preparing Docker volume..."
docker volume create spark-data 2>/dev/null || true

echo "Running Bronze stage..."
docker run --rm --user root --network "$NETWORK_NAME" \
  -v "$WORKSPACE:/workspace" \
  -v spark-data:/mnt/data \
  "$SPARK_IMAGE" \
  bash -c "mkdir -p /mnt/data && /opt/spark/bin/spark-submit \
  --master local[2] \
  --conf spark.jars.ivy=$IVY_CACHE \
  --packages com.datastax.spark:spark-cassandra-connector_2.12:3.4.1 \
  /workspace/databricks/bronze_layer.py"

echo "Running Silver stage..."
docker run --rm --user root --network "$NETWORK_NAME" \
  -v "$WORKSPACE:/workspace" \
  -v spark-data:/mnt/data \
  "$SPARK_IMAGE" \
  bash -c "mkdir -p /mnt/data && /opt/spark/bin/spark-submit \
  --master local[2] \
  --conf spark.jars.ivy=$IVY_CACHE \
  /workspace/databricks/silver_layer.py"

echo "Running Gold stage..."
docker run --rm --user root --network "$NETWORK_NAME" \
  -v "$WORKSPACE:/workspace" \
  -v spark-data:/mnt/data \
  "$SPARK_IMAGE" \
  bash -c "mkdir -p /mnt/data && /opt/spark/bin/spark-submit \
  --master local[2] \
  --conf spark.jars.ivy=$IVY_CACHE \
  /workspace/databricks/gold_layer.py"

echo "Running Graph stage..."
docker run --rm --user root --network "$NETWORK_NAME" \
  -v "$WORKSPACE:/workspace" \
  -v spark-data:/mnt/data \
  "$SPARK_IMAGE" \
  bash -c "mkdir -p /mnt/data && /opt/spark/bin/spark-submit \
  --master local[2] \
  --conf spark.jars.ivy=$IVY_CACHE \
  /workspace/databricks/graph_layer.py"

cat <<'EOF'
✅ Databricks Spark pipeline completed.
- Bronze parquet: ./data/papers_bronze_parquet
- Silver parquet: ./data/papers_silver_parquet
- Gold parquet:   ./data/papers_gold
- Graph parquet:  ./data/papers_graph
EOF
