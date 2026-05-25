# 🚀 Launch Kafka Streaming Pipeline (Windows)

Write-Host "════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "🚀 KAFKA STREAMING PIPELINE - LAUNCHER" -ForegroundColor Cyan
Write-Host "════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Check if running in the right directory
if (-not (Test-Path "docker-compose.yml")) {
    Write-Host "❌ docker-compose.yml not found. Run from project root!" -ForegroundColor Red
    exit 1
}

# Parse arguments
$Action = $args[0] -or "start"
$Continuous = $args[1] -or $false

Write-Host "🐳 Starting Docker services..." -ForegroundColor Green
docker-compose up -d zookeeper kafka cassandra

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Docker compose failed!" -ForegroundColor Red
    exit 1
}

Write-Host "⏳ Waiting for Kafka to become ready (30 seconds)..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

Write-Host "🔍 Checking Kafka status..." -ForegroundColor Green
docker exec kafka_arxiv kafka-broker-api-versions.sh --bootstrap-server localhost:9092

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Kafka failed to become ready!" -ForegroundColor Red
    exit 1
}

Write-Host "📋 Creating Kafka topic..." -ForegroundColor Green
docker exec kafka_arxiv kafka-topics.sh `
    --create `
    --topic arxiv-papers-raw `
    --bootstrap-server localhost:9092 `
    --partitions 3 `
    --replication-factor 1 `
    --if-not-exists

Write-Host ""
Write-Host "════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "✅ Infrastructure is ready!" -ForegroundColor Cyan
Write-Host "════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "🚀 Launching Kafka streaming pipeline..." -ForegroundColor Green
Write-Host ""

$Args = @("scripts/orchestrate_kafka.py", "--action", "start")
if ($Continuous) {
    $Args += "--continuous"
}

python @Args
