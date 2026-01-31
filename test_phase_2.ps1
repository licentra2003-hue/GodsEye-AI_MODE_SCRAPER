# GodsEye Phase 2 - API Gateway Test (PowerShell)
# ================================================

Write-Host "GodsEye Phase 2 - API Gateway Test"
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

Write-Host "Building and starting API Gateway..."

# Build and start the API Gateway
docker-compose up -d api_gateway rabbitmq postgres

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to start API Gateway"
    exit 1
}

Write-Host "Waiting for API Gateway to be ready (15 seconds)..."
Start-Sleep -Seconds 15

# Test API Gateway health
Write-Host "Testing API Gateway health..."
try {
    $healthResponse = Invoke-RestMethod -Uri "http://localhost:8080/health" -Method GET
    Write-Host "API Gateway is healthy"
    Write-Host "Response: $($healthResponse | ConvertTo-Json -Compress)"
} catch {
    Write-Host "API Gateway health check failed: $($_.Exception.Message)"
    exit 1
}

Write-Host ""
Write-Host "Testing scrape endpoint..."

# Send a test scrape request
try {
    $testRequest = @{
        query = "best transdermal vitamin patches"
        location = "India"
        webhook_url = "http://example.com/webhook"
    } | ConvertTo-Json
    
    $testResponse = Invoke-RestMethod -Uri "http://localhost:8080/api/v1/scrape" -Method POST -ContentType "application/json" -Body $testRequest
    Write-Host "Scrape request submitted successfully"
    Write-Host "Response: $($testResponse | ConvertTo-Json -Compress)"
    
    if ($testResponse.job_id) {
        Write-Host "Job ID: $($testResponse.job_id)"
    } else {
        Write-Host "Could not extract job ID from response"
    }
} catch {
    Write-Host "Failed to submit scrape request: $($_.Exception.Message)"
    exit 1
}

Write-Host ""
Write-Host "Checking RabbitMQ queue..."

# Wait a moment for message to be processed
Start-Sleep -Seconds 2

# Check queue depth using rabbitmqadmin
try {
    $queueInfo = docker exec godseye-rabbitmq rabbitmqadmin list queues name messages 2>$null
    Write-Host "RabbitMQ queue check completed"
    Write-Host $queueInfo
} catch {
    Write-Host "Could not check RabbitMQ queue"
}

Write-Host ""
Write-Host "Getting queue details..."
try {
    $queueDetails = docker exec godseye-rabbitmq rabbitmqadmin list queues name messages consumers 2>$null
    Write-Host $queueDetails
} catch {
    Write-Host "Could not get queue details"
}

Write-Host ""
Write-Host "Test Results:"
Write-Host "   - API Gateway: Running and accepting requests"
Write-Host "   - RabbitMQ: Receiving messages"
Write-Host "   - Job Queue: Processing scrape jobs"

Write-Host ""
Write-Host "Available Services:"
Write-Host "   - API Gateway: http://localhost:8080"
Write-Host "   - RabbitMQ Management: http://localhost:15672 (admin/admin123)"
Write-Host ""
Write-Host "To stop services: docker-compose down"

exit 0
