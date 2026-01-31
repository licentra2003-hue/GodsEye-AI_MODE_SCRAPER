"""
Run project locally without Docker - using Supabase directly
"""
import os
import subprocess
import sys
import time
from pathlib import Path
import threading
import requests

def run_api_gateway():
    """Run API Gateway in a separate thread"""
    print("🌐 Starting API Gateway...")
    os.environ["RABBITMQ_URL"] = "amqp://admin:admin123@localhost:5672/"
    os.environ["POSTGRES_URL"] = "postgres://postgres:postgres123@localhost:5432/godseye"
    os.environ["GATEWAY_PORT"] = "8080"
    
    # Change to gateway directory and run
    os.chdir("gateway")
    subprocess.run(["go", "run", "main.go"])
    os.chdir("..")

def run_worker():
    """Run Worker in a separate thread"""
    print("🤖 Starting Worker...")
    os.environ["RABBITMQ_URL"] = "amqp://admin:admin123@localhost:5672/"
    os.environ["POSTGRES_URL"] = "postgres://postgres:postgres123@localhost:5432/godseye"
    os.environ["SUPABASE_URL"] = "https://bnrpcmwkqqdmweoxkmth.supabase.co"
    os.environ["SUPABASE_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJucnBjbXdrcXFkbXdlb3hrbXRoIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MDgwMDU2NiwiZXhwIjoyMDc2Mzc2NTY2fQ.5bWehH-YMcXq-OYDamtMeplEqZuUy2xTHDieB9D8eVc"
    os.environ["HEADLESS"] = "true"
    os.environ["PROXY_SERVER"] = ""
    os.environ["PROXY_USERNAME"] = ""
    os.environ["PROXY_PASSWORD"] = ""
    
    # Change to worker directory and run
    os.chdir("worker")
    subprocess.run(["python", "worker_main.py"])
    os.chdir("..")

def test_direct_scrape():
    """Test scraper directly without API Gateway"""
    print("\n🧪 Testing Direct Scraping...")
    
    # Import worker and test directly
    sys.path.append(str(Path("worker")))
    from worker_main import WorkerService
    
    # Create worker instance
    worker = WorkerService()
    
    # Simulate a job
    import json
    job_data = {
        'job_id': 'test-local-123',
        'query': 'best mmps platform',
        'location': 'India',
        'product_id': 'b36b116e-0c19-4fa0-b669-835bd76c820e'
    }
    
    class MockChannel:
        def basic_ack(self, delivery_tag):
            print(f"✅ Job acknowledged")
        def basic_nack(self, delivery_tag, requeue=False):
            print(f"❌ Job failed, requeue={requeue}")
    
    class MockMethod:
        delivery_tag = 'test-tag'
    
    # Run the job
    import asyncio
    asyncio.run(worker._process_job(
        MockChannel(),
        MockMethod(),
        None,
        json.dumps(job_data).encode()
    ))

def main():
    print("🚀 GodsEye Local Runner (No Docker)")
    print("="*50)
    
    choice = input("\nSelect option:\n1. Test Direct Scraping (Recommended)\n2. Run Full Stack (API Gateway + Worker)\n3. Run API Gateway Only\n4. Run Worker Only\n\nChoice (1-4): ")
    
    if choice == "1":
        test_direct_scrape()
    elif choice == "2":
        print("\n📦 Starting Full Stack...")
        # Start API Gateway in thread
        gateway_thread = threading.Thread(target=run_api_gateway)
        gateway_thread.daemon = True
        gateway_thread.start()
        
        # Wait for API Gateway
        time.sleep(3)
        
        # Start Worker in thread
        worker_thread = threading.Thread(target=run_worker)
        worker_thread.daemon = True
        worker_thread.start()
        
        print("\n✅ Services started!")
        print("📊 API Gateway: http://localhost:8080")
        print("\n🧪 Test with:")
        print("curl -X POST http://localhost:8080/scrape \\")
        print("  -H 'Content-Type: application/json' \\")
        print("  -d '{\"query\": \"best mmps platform\", \"location\": \"India\", \"product_id\": \"b36b116e-0c19-4fa0-b669-835bd76c820e\"}'")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Stopping...")
    elif choice == "3":
        run_api_gateway()
    elif choice == "4":
        run_worker()
    else:
        print("❌ Invalid choice")

if __name__ == "__main__":
    main()
