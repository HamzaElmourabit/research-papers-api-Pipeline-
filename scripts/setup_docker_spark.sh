#!/bin/bash
# Docker Spark Pipeline Setup - Step by Step

set -e  # Exit on error

echo "=================================================="
echo "  DOCKER SPARK PIPELINE SETUP"
echo "=================================================="
echo ""

# Step 1: Check Docker
echo "[1/6] Checking Docker..."
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Install Docker Desktop first."
    exit 1
fi

DOCKER_VERSION=$(docker --version)
echo "✓ Docker installed: $DOCKER_VERSION"
echo ""

# Step 2: Verify Docker daemon is running
echo "[2/6] Testing Docker daemon..."
if ! docker ps &> /dev/null; then
    echo "⚠️  Docker daemon not responding. Attempting to start..."
    # On Windows with WSL, Docker Desktop needs to be running
    echo "💡 Try: Start → Search for 'Docker Desktop' → Open it"
    exit 1
fi
echo "✓ Docker daemon responsive"
echo ""

# Step 3: Start core services (without Kafdrop due to image issues)
echo "[3/6] Starting Kafka and Cassandra services..."
docker compose up -d kafka cassandra zookeeper

# Wait for services to be ready
echo "⏳ Waiting for services to start (30 seconds)..."
sleep 30

# Verify services
echo ""
echo "[4/6] Verifying services..."
if docker compose ps | grep -q "healthy"; then
    echo "✓ Services started successfully"
else
    echo "⚠️  Some services may still be starting, continuing anyway..."
fi

docker compose ps
echo ""

# Step 5: Check Cassandra connectivity
echo "[5/6] Testing Cassandra connectivity..."
if docker exec cassandra_arxiv cqlsh -e "SELECT cluster_name FROM system.local;" 2>/dev/null | grep -q "cluster"; then
    echo "✓ Cassandra is ready"
else
    echo "⏳ Cassandra still initializing, this is normal..."
fi
echo ""

# Step 6: Prepare Spark execution
echo "[6/6] Ready for Spark execution"
echo ""
echo "=================================================="
echo "  NEXT STEPS"
echo "=================================================="
echo ""
echo "Option A: Run Bronze Layer (Load from Cassandra)"
echo "  docker run --it --network researchpapersapi-copy_arxiv_network -v \$(pwd):/workspace -v \$(pwd)/data:/mnt/data apache/spark:3.4.1 /opt/spark/bin/spark-submit --master local[2] --conf spark.jars.ivy=/tmp/.ivy2 --packages com.datastax.spark:spark-cassandra-connector_2.12:3.4.1 /workspace/databricks/bronze_layer.py"
echo ""
echo "Option B: Run full pipeline sequentially"
echo "  bash ./scripts/run_spark_pipeline.sh"
echo ""
echo "Option C: Check Kafka messages (if containers are running)"
echo "  docker exec kafka_broker kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic arxiv-papers-raw --max-messages 1 --from-beginning"
echo ""
echo "=================================================="
