# Start the FastAPI server
# Usage: .\scripts\run_api.ps1

Write-Host "🚀 Starting ArXiv API Server..." -ForegroundColor Green

# Vérifier si Cassandra est en cours d'exécution
Write-Host "📊 Checking Cassandra connection..." -ForegroundColor Yellow

$cassandraHost = $env:CASSANDRA_HOST -or "localhost"
$cassandraPort = $env:CASSANDRA_PORT -or 9042

try {
    $tcpClient = New-Object System.Net.Sockets.TcpClient
    $tcpClient.Connect($cassandraHost, $cassandraPort)
    $tcpClient.Close()
    Write-Host "✅ Cassandra is running at $cassandraHost`:$cassandraPort" -ForegroundColor Green
} catch {
    Write-Host "❌ Cassandra is NOT running. Start it with: docker-compose up -d cassandra" -ForegroundColor Red
    exit 1
}

# Démarrer le serveur API
Write-Host ""
Write-Host "Starting API on port 8000..." -ForegroundColor Cyan
Write-Host "📚 API Docs: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "📖 ReDoc: http://localhost:8000/redoc" -ForegroundColor Cyan
Write-Host ""

python scripts/api_server.py
