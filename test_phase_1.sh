#!/bin/bash

echo "🚀 GodsEye Phase 1 Infrastructure Test"
echo "======================================"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

echo "📦 Spinning up infrastructure with Docker Compose..."

# Spin up services in detached mode
docker-compose up -d

if [ $? -ne 0 ]; then
    echo "❌ Failed to start Docker Compose services"
    exit 1
fi

echo "⏳ Waiting for services to initialize (30 seconds)..."
sleep 30

echo "🔍 Installing required Python packages..."
pip install psycopg2-binary pika > /dev/null 2>&1

echo "🏥 Running infrastructure health check..."
python check_infra.py

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Infrastructure Ready!"
    echo ""
    echo "🌐 Service URLs:"
    echo "   - RabbitMQ Management: http://localhost:15672 (admin/admin123)"
    echo "   - PostgreSQL: localhost:5432 (postgres/postgres123)"
    echo ""
    echo "🎯 Next Steps:"
    echo "   1. Implement the Go API Gateway"
    echo "   2. Implement the Python Worker Service"
    echo ""
    echo "🛑 To stop services: docker-compose down"
    exit 0
else
    echo ""
    echo "❌ Infrastructure test failed!"
    echo ""
    echo "🔍 Debugging tips:"
    echo "   - Check service logs: docker-compose logs [service_name]"
    echo "   - Verify ports are not in use"
    echo "   - Ensure Docker has enough resources"
    echo ""
    echo "🛑 To cleanup: docker-compose down -v"
    exit 1
fi
