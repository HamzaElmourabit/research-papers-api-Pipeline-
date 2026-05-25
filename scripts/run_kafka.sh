#!/bin/bash
# 🚀 Launch Kafka Streaming Pipeline (Linux/macOS)

echo "════════════════════════════════════════════════════════"
echo "🚀 KAFKA STREAMING PIPELINE - LAUNCHER"
echo "════════════════════════════════════════════════════════"

# Check if running in the right directory
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ docker-compose.yml not found. Run from project root!"
    exit 1
fi

# Parse arguments
ACTION=${1:-start}
CONTINUOUS=${2:-0}

# Start Docker services
echo "🐳 Starting Docker services..."
docker-compose up -d zookeeper kafka cassandra

# Wait for Kafka to be ready
echo "⏳ Waiting for Kafka to become ready..."
sleep 10

# Check Kafka health
echo "🔍 Checking Kafka status..."
docker exec kafka_arxiv kafka-broker-api-versions.sh --bootstrap-server localhost:9092
if [ $? -ne 0 ]; then
    echo "❌ Kafka failed to become ready!"
    exit 1
fi

# Create topic
echo "📋 Creating Kafka topic..."
docker exec kafka_arxiv kafka-topics.sh \
    --create \
    --topic arxiv-papers-raw \
    --bootstrap-server localhost:9092 \
    --partitions 3 \
    --replication-factor 1 \
    --if-not-exists

echo ""
echo "════════════════════════════════════════════════════════"
echo "✅ Infrastructure is ready!"
echo "════════════════════════════════════════════════════════"
echo ""
echo "🚀 Launching Kafka streaming pipeline..."
echo ""

if [ "$CONTINUOUS" -eq 1 ]; then
    python scripts/orchestrate_kafka.py --action start --continuous
else
    python scripts/orchestrate_kafka.py --action start
fi
