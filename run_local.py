"""
Run the project locally without Docker to simulate deployment
"""
import os
import subprocess
import sys
import time
from pathlib import Path

def run_command(cmd, cwd=None, shell=True):
    """Run a command and return the process"""
    print(f"🚀 Running: {cmd}")
    process = subprocess.Popen(cmd, cwd=cwd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return process

def check_service(url, service_name):
    """Check if a service is running"""
    import requests
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            print(f"✅ {service_name} is running at {url}")
            return True
    except:
        print(f"❌ {service_name} is not responding at {url}")
    return False

def main():
    print("🚀 GodsEye Local Deployment Simulator")
    print("="*50)
    
    # Set environment variables
    os.environ["RABBITMQ_URL"] = "amqp://admin:admin123@localhost:5672/"
    os.environ["POSTGRES_URL"] = "postgres://postgres:postgres123@localhost:5432/godseye"
    os.environ["GATEWAY_PORT"] = "8080"
    os.environ["HEADLESS"] = "true"
    
    # Disable proxy for local testing
    os.environ["PROXY_SERVER"] = ""
    os.environ["PROXY_USERNAME"] = ""
    os.environ["PROXY_PASSWORD"] = ""
    
    print("\n📦 Starting Services...")
    
    # Start RabbitMQ (using Docker)
    print("\n🐰 Starting RabbitMQ...")
    rabbitmq_process = run_command(
        'docker run -d --name godseye-rabbitmq-local -p 5672:5672 -p 15672:15672 -e RABBITMQ_DEFAULT_USER=admin -e RABBITMQ_DEFAULT_PASS=admin123 rabbitmq:3.12-management-alpine'
    )
    
    # Wait for RabbitMQ to start
    time.sleep(10)
    
    # Start PostgreSQL (using Docker)
    print("\n🐘 Starting PostgreSQL...")
    postgres_process = run_command(
        'docker run -d --name godseye-postgres-local -p 5432:5432 -e POSTGRES_DB=godseye -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres123 postgres:15-alpine'
    )
    
    # Wait for PostgreSQL to start
    time.sleep(10)
    
    # Start API Gateway
    print("\n🌐 Starting API Gateway...")
    gateway_process = run_command(
        'cd gateway && go run main.go',
        cwd=Path.cwd()
    )
    
    # Wait for API Gateway to start
    time.sleep(5)
    
    # Start Worker
    print("\n🤖 Starting Worker...")
    worker_process = run_command(
        'cd worker && python worker_main.py',
        cwd=Path.cwd()
    )
    
    print("\n✅ All services started!")
    print("\n📊 Service URLs:")
    print("   - API Gateway: http://localhost:8080")
    print("   - RabbitMQ Management: http://localhost:15672 (admin/admin123)")
    print("   - PostgreSQL: localhost:5432")
    
    print("\n🧪 Testing API Gateway...")
    import requests
    
    # Test health endpoint
    try:
        response = requests.get("http://localhost:8080/health", timeout=5)
        if response.status_code == 200:
            print("✅ API Gateway is healthy")
        else:
            print(f"⚠ API Gateway returned status: {response.status_code}")
    except Exception as e:
        print(f"❌ API Gateway not responding: {e}")
    
    print("\n📝 To test the scraper, run:")
    print("   curl -X POST http://localhost:8080/scrape \\")
    print("     -H 'Content-Type: application/json' \\")
    print("     -d '{\"query\": \"best mmps platform\", \"location\": \"India\", \"product_id\": \"b36b116e-0c19-4fa0-b669-835bd76c820e\"}'")
    
    print("\n🛑 Press Ctrl+C to stop all services")
    
    try:
        # Keep running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping services...")
        
        # Stop processes
        for process in [gateway_process, worker_process]:
            if process:
                process.terminate()
        
        # Stop Docker containers
        run_command('docker stop godseye-rabbitmq-local godseye-postgres-local')
        run_command('docker rm godseye-rabbitmq-local godseye-postgres-local')
        
        print("✅ All services stopped")

if __name__ == "__main__":
    main()
