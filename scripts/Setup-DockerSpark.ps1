# Docker Spark Pipeline Setup - Windows PowerShell
# Run this after Docker Desktop is properly started

Write-Host "=================================================="
Write-Host "  DOCKER SPARK PIPELINE SETUP"
Write-Host "=================================================="
Write-Host ""

# Step 1: Check Docker
Write-Host "[1/6] Checking Docker..." -ForegroundColor Cyan
$dockerVersion = docker --version
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Docker not found. Install Docker Desktop first." -ForegroundColor Red
    exit 1
}
Write-Host "✓ Docker installed: $dockerVersion" -ForegroundColor Green
Write-Host ""

# Step 2: Verify Docker daemon
Write-Host "[2/6] Testing Docker daemon..." -ForegroundColor Cyan
$dockerPs = docker ps 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Docker daemon not responding" -ForegroundColor Red
    Write-Host "💡 Actions to try:" -ForegroundColor Yellow
    Write-Host "   1. Start Docker Desktop application"
    Write-Host "   2. Wait 30 seconds for initialization"
    Write-Host "   3. Run this script again"
    Write-Host ""
    Write-Host "If still failing:"
    Write-Host "   - Restart Docker: Right-click Docker icon → Quit → Reopen"
    Write-Host "   - Check WSL2 is installed: wsl --list --verbose"
    exit 1
}
Write-Host "✓ Docker daemon responsive" -ForegroundColor Green
Write-Host ""

# Step 3: Start services
Write-Host "[3/6] Starting Kafka, Cassandra, Zookeeper..." -ForegroundColor Cyan
docker compose up -d kafka cassandra zookeeper
if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️  docker compose up failed. Checking images..." -ForegroundColor Yellow
    Write-Host "This may take a few minutes while images download..." -ForegroundColor Yellow
}
Write-Host ""

# Wait for services
Write-Host "⏳ Waiting for services to initialize (40 seconds)..." -ForegroundColor Yellow
Start-Sleep -Seconds 40

# Step 4: Show status
Write-Host "[4/6] Service Status:" -ForegroundColor Cyan
docker compose ps
Write-Host ""

# Step 5: Test Cassandra
Write-Host "[5/6] Testing Cassandra connectivity..." -ForegroundColor Cyan
try {
    $cassandraTest = docker exec cassandra_arxiv cqlsh -e "SELECT cluster_name FROM system.local;" 2>&1
    if ($cassandraTest -match "cluster") {
        Write-Host "✓ Cassandra is accessible" -ForegroundColor Green
    } else {
        Write-Host "⏳ Cassandra may still be initializing" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⏳ Cassandra still initializing (normal on first run)" -ForegroundColor Yellow
}
Write-Host ""

# Step 6: Summary
Write-Host "=================================================="
Write-Host "  READY FOR SPARK EXECUTION" -ForegroundColor Green
Write-Host "=================================================="
Write-Host ""
Write-Host "Three ways to proceed:" -ForegroundColor Cyan
Write-Host ""
Write-Host "OPTION A - Run Bronze Layer only:" -ForegroundColor Yellow
Write-Host '  docker run --it --network researchpapersapi-copy_arxiv_network `' 
Write-Host '    -v "$(Get-Location):/workspace" `'
Write-Host '    -v "$(Get-Location)\data:/mnt/data" `'
Write-Host '    apache/spark:3.4.1 /opt/spark/bin/spark-submit `'
Write-Host '    --master local[2] --conf spark.jars.ivy=/tmp/.ivy2 `'
Write-Host '    --packages com.datastax.spark:spark-cassandra-connector_2.12:3.4.1 /workspace/databricks/bronze_layer.py'
Write-Host ""

Write-Host "OPTION B - Run full pipeline (Bronze → Silver → Gold):" -ForegroundColor Yellow
Write-Host '  $env:SPARK_DOCKER="yes"; python .\scripts\run_spark_pipeline.py'
Write-Host ""

Write-Host "OPTION C - Monitor Kafka messages:" -ForegroundColor Yellow
Write-Host '  docker exec kafka_broker kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic arxiv-papers-raw --max-messages 3'
Write-Host ""

Write-Host "OPTION D - Query Cassandra:" -ForegroundColor Yellow
Write-Host '  docker exec cassandra_arxiv cqlsh -e "USE arxiv; SELECT COUNT(*) FROM papers_raw;"'
Write-Host ""
Write-Host "=================================================="
