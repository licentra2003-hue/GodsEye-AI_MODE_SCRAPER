"""
Alternative Docker setup using Docker CLI without Desktop
"""
import subprocess
import time
import os

def setup_docker_services():
    print("🚀 Setting up Docker Services (CLI Mode)")
    print("="*50)
    
    # Check if Docker CLI is working
    try:
        result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
        print(f"✅ Docker CLI: {result.stdout.strip()}")
    except:
        print("❌ Docker CLI not found")
        return False
    
    # Remove version from docker-compose.yml
    print("\n📝 Updating docker-compose.yml...")
    with open('docker-compose.yml', 'r') as f:
        content = f.read()
    
    # Remove version line
    content = '\n'.join([line for line in content.split('\n') if not line.startswith('version:')])
    
    with open('docker-compose.yml', 'w') as f:
        f.write(content)
    print("✅ Removed obsolete version from docker-compose.yml")
    
    # Try using docker compose (newer syntax)
    print("\n🐳 Starting services with docker compose...")
    try:
        # Start RabbitMQ first
        print("\n🐰 Starting RabbitMQ...")
        subprocess.run(['docker', 'run', '-d', '--name', 'godseye-rabbitmq', 
                       '-p', '5672:5672', '-p', '15672:15672',
                       '-e', 'RABBITMQ_DEFAULT_USER=admin',
                       '-e', 'RABBITMQ_DEFAULT_PASS=admin123',
                       'rabbitmq:3.12-management-alpine'], check=True)
        
        # Wait for RabbitMQ
        print("⏳ Waiting for RabbitMQ to be ready...")
        time.sleep(15)
        
        # Start PostgreSQL
        print("\n🐘 Starting PostgreSQL...")
        subprocess.run(['docker', 'run', '-d', '--name', 'godseye-postgres',
                       '-p', '5432:5432',
                       '-e', 'POSTGRES_DB=godseye',
                       '-e', 'POSTGRES_USER=postgres',
                       '-e', 'POSTGRES_PASSWORD=postgres123',
                       'postgres:15-alpine'], check=True)
        
        # Wait for PostgreSQL
        print("⏳ Waiting for PostgreSQL to be ready...")
        time.sleep(10)
        
        # Build and run API Gateway
        print("\n🌐 Building API Gateway...")
        subprocess.run(['docker', 'build', '-t', 'godseye-gateway', './gateway'], check=True)
        
        print("\n🌐 Starting API Gateway...")
        subprocess.run(['docker', 'run', '-d', '--name', 'godseye-gateway',
                       '-p', '8080:8080',
                       '-e', 'RABBITMQ_URL=amqp://admin:admin123@host.docker.internal:5672/',
                       '-e', 'POSTGRES_URL=postgres://postgres:postgres123@host.docker.internal:5432/godseye',
                       '-e', 'GATEWAY_PORT=8080',
                       'godseye-gateway'], check=True)
        
        # Build and run Worker
        print("\n🤖 Building Worker...")
        subprocess.run(['docker', 'build', '-t', 'godseye-worker', './worker'], check=True)
        
        print("\n🤖 Starting Worker...")
        subprocess.run(['docker', 'run', '-d', '--name', 'godseye-worker',
                       '-e', 'RABBITMQ_URL=amqp://admin:admin123@host.docker.internal:5672/',
                       '-e', 'POSTGRES_URL=postgres://postgres:postgres123@host.docker.internal:5432/godseye',
                       '-e', 'SUPABASE_URL=https://bnrpcmwkqqdmweoxkmth.supabase.co',
                       '-e', 'SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJucnBjbXdrcXFkbXdlb3hrbXRoIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MDgwMDU2NiwiZXhwIjoyMDc2Mzc2NTY2fQ.5bWehH-YMcXq-OYDamtMeplEqZuUy2xTHDieB9D8eVc',
                       '-e', 'HEADLESS=true',
                       '-e', 'PROXY_SERVER=',
                       '-e', 'PROXY_USERNAME=',
                       '-e', 'PROXY_PASSWORD=',
                       '--add-host', 'host.docker.internal:host-gateway',
                       'godseye-worker'], check=True)
        
        print("\n✅ All services started!")
        print("\n📊 Service URLs:")
        print("   - API Gateway: http://localhost:8080")
        print("   - RabbitMQ Management: http://localhost:15672 (admin/admin123)")
        print("   - PostgreSQL: localhost:5432")
        
        print("\n🧪 Test with:")
        print("curl -X POST http://localhost:8080/scrape \\")
        print("  -H 'Content-Type: application/json' \\")
        print("  -d '{\"query\": \"best mmps platform\", \"location\": \"India\", \"product_id\": \"b36b116e-0c19-4fa0-b669-835bd76c820e\"}'")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return False

def cleanup_services():
    print("\n🧹 Cleaning up services...")
    services = ['godseye-worker', 'godseye-gateway', 'godseye-postgres', 'godseye-rabbitmq']
    
    for service in services:
        try:
            subprocess.run(['docker', 'stop', service], check=False)
            subprocess.run(['docker', 'rm', service], check=False)
            print(f"✅ Removed {service}")
        except:
            pass

if __name__ == "__main__":
    if setup_docker_services():
        input("\n🛑 Press Enter to stop all services...")
        cleanup_services()
    else:
        print("\n❌ Failed to start services")
