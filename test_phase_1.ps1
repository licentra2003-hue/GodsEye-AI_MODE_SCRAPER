# GodsEye Phase 1 Infrastructure Test
# ======================================

Write-Host "GodsEye Phase 1 Infrastructure Test"
Write-Host "======================================"

# Check if Docker is running
try {
    $dockerInfo = docker info 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Docker is not running. Please start Docker first."
        exit 1
    }
} catch {
    Write-Host "Docker is not running. Please start Docker first."
    exit 1
}

Write-Host "Spinning up infrastructure with Docker Compose..."

# Spin up services in detached mode
docker-compose up -d

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to start Docker Compose services"
    exit 1
}

Write-Host "Waiting for services to initialize (30 seconds)..."
Start-Sleep -Seconds 30

Write-Host "Installing required Python packages..."
pip install psycopg2-binary pika 2>$null

Write-Host "Running infrastructure health check..."
python check_infra.py

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "Infrastructure Ready!"
    Write-Host ""
    Write-Host "Service URLs:"
    Write-Host "   - RabbitMQ Management: http://localhost:15672 (admin/admin123)"
    Write-Host "   - PostgreSQL: localhost:5432 (postgres/postgres123)"
    Write-Host ""
    Write-Host "Next Steps:"
    Write-Host "   1. Implement the Go API Gateway"
    Write-Host "   2. Implement the Python Worker Service"
    Write-Host ""
    Write-Host "To stop services: docker-compose down"
    exit 0
} else {
    Write-Host ""
    Write-Host "Infrastructure test failed!"
    Write-Host ""
    Write-Host "Debugging tips:"
    Write-Host "   - Check service logs: docker-compose logs [service_name]"
    Write-Host "   - Verify ports are not in use"
    Write-Host "   - Ensure Docker has enough resources"
    Write-Host ""
    Write-Host "To cleanup: docker-compose down -v"
    exit 1
}
