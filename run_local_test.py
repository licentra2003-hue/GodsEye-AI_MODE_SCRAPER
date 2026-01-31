#!/usr/bin/env python3
"""
Run GodsEye services locally without Docker
"""

import asyncio
import subprocess
import sys
import time
import requests
from pathlib import Path

def check_service(url, service_name, timeout=30, auth=None):
    """Check if a service is healthy"""
    print(f"⏳ Checking {service_name} at {url}...")
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            kwargs = {"timeout": 5}
            if auth:
                kwargs["auth"] = auth
            response = requests.get(url, **kwargs)
            if response.status_code == 200:
                print(f"✅ {service_name} is healthy")
                return True
        except:
            pass
        time.sleep(1)
    
    print(f"❌ {service_name} health check failed")
    return False

def run_command(cmd, cwd=None):
    """Run a command and return the process"""
    print(f"🚀 Starting: {' '.join(cmd)}")
    if cwd:
        print(f"   Directory: {cwd}")
    
    if sys.platform == "win32":
        process = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
    else:
        process = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
    
    return process

def monitor_process(process, name):
    """Monitor process output"""
    try:
        for line in iter(process.stdout.readline, ''):
            if line:
                print(f"[{name}] {line.strip()}")
    except:
        pass

async def main():
    """Main function to run all services"""
    print("🚀 GodsEye Local Test Runner")
    print("=" * 50)
    
    # Start RabbitMQ (if not running)
    print("\n🐰 Checking RabbitMQ...")
    try:
        # Check if container already exists
        result = subprocess.run(
            ["docker", "ps", "-a", "--filter", "name=godseye-rabbitmq-local"],
            capture_output=True,
            text=True
        )
        
        if "godseye-rabbitmq-local" in result.stdout:
            print("✅ RabbitMQ container already exists")
            # Check if it's running
            if "Up" in result.stdout:
                print("✅ RabbitMQ is already running")
            else:
                print("🚀 Starting existing RabbitMQ container...")
                subprocess.run(["docker", "start", "godseye-rabbitmq-local"], check=True)
        else:
            print("🚀 Starting new RabbitMQ container...")
            subprocess.run([
                "docker", "run", "-d",
                "--name", "godseye-rabbitmq-local",
                "-p", "5672:5672",
                "-p", "15672:15672",
                "-e", "RABBITMQ_DEFAULT_USER=admin",
                "-e", "RABBITMQ_DEFAULT_PASS=admin123",
                "rabbitmq:3.12-management-alpine"
            ], check=True)
        
        # Wait for RabbitMQ to be ready
        if not check_service("http://localhost:15672/api/overview", "RabbitMQ", 30, auth=("admin", "admin123")):
            print("❌ RabbitMQ failed to start")
            return
    except Exception as e:
        print(f"❌ RabbitMQ error: {e}")
        return
    
    # Start PostgreSQL (if not running)
    print("\n🐘 Starting PostgreSQL...")
    try:
        postgres_process = run_command([
            "docker", "run", "-d",
            "--name", "godseye-postgres-local",
            "-p", "5432:5432",
            "-e", "POSTGRES_DB=godseye",
            "-e", "POSTGRES_USER=postgres",
            "-e", "POSTGRES_PASSWORD=postgres123",
            "postgres:15-alpine"
        ])
        
        # Wait for PostgreSQL to be ready
        if not check_service("http://localhost:5432", "PostgreSQL", 30):
            print("⚠ PostgreSQL might not be ready (HTTP check not applicable)")
    except Exception as e:
        print(f"⚠ PostgreSQL might already be running: {e}")
    
    # Start Go Gateway
    print("\n🌐 Starting Go Gateway...")
    gateway_process = run_command([
        "go", "run", "main.go"
    ], cwd="gateway")
    
    # Wait for Gateway to be ready
    if not check_service("http://localhost:8080/health", "Gateway", 30):
        print("❌ Gateway failed to start")
        return
    
    # Start Python Worker
    print("\n🐍 Starting Python Worker...")
    worker_process = run_command([
        "python", "worker_main.py"
    ], cwd="worker")
    
    # Test the API
    print("\n🧪 Testing API...")
    time.sleep(2)  # Give worker time to connect
    
    # Test health endpoint
    try:
        response = requests.get("http://localhost:8080/health")
        print(f"✅ Health check: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return
    
    # Test scrape endpoint
    try:
        scrape_data = {
            "query": "best mmps platform",
            "location": "India"
        }
        response = requests.post(
            "http://localhost:8080/api/v1/scrape",
            json=scrape_data
        )
        print(f"✅ Scrape request: {response.status_code}")
        print(f"   Response: {response.json()}")
        
        if response.status_code == 202:
            job_id = response.json().get('job_id')
            print(f"📋 Job ID: {job_id}")
            
            # Wait for job completion
            print("⏳ Waiting for job completion...")
            time.sleep(10)
            
    except Exception as e:
        print(f"❌ Scrape request failed: {e}")
    
    print("\n✅ All services are running!")
    print("📊 RabbitMQ Management: http://localhost:15672 (admin/admin123)")
    print("🌐 Gateway: http://localhost:8080")
    print("\nPress Ctrl+C to stop all services...")
    
    try:
        # Keep running and monitor processes
        while True:
            time.sleep(1)
            
            # Check if processes are still running
            if gateway_process.poll() is not None:
                print("❌ Gateway process stopped")
                break
            
            if worker_process.poll() is not None:
                print("❌ Worker process stopped")
                break
                
    except KeyboardInterrupt:
        print("\n🛑 Stopping services...")
        
        # Stop processes
        gateway_process.terminate()
        worker_process.terminate()
        
        # Stop Docker containers
        try:
            subprocess.run(["docker", "stop", "godseye-rabbitmq-local"], check=False)
            subprocess.run(["docker", "rm", "godseye-rabbitmq-local"], check=False)
            subprocess.run(["docker", "stop", "godseye-postgres-local"], check=False)
            subprocess.run(["docker", "rm", "godseye-postgres-local"], check=False)
        except:
            pass
        
        print("✅ All services stopped")

if __name__ == "__main__":
    asyncio.run(main())
