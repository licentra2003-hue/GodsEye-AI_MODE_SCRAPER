"""
Test the running API Gateway
"""
import requests
import json
import time

def test_api():
    print("🧪 Testing GodsEye API Gateway")
    print("="*50)
    
    # Test health endpoint
    print("\n1️⃣ Testing Health Endpoint...")
    try:
        response = requests.get("http://localhost:8080/health", timeout=5)
        print(f"✅ Health Status: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return
    
    # Test scrape endpoint
    print("\n2️⃣ Testing Scrape Endpoint...")
    scrape_data = {
        "query": "best mmps platform",
        "location": "India",
        "product_id": "b36b116e-0c19-4fa0-b669-835bd76c820e"
    }
    
    try:
        response = requests.post(
            "http://localhost:8080/api/v1/scrape",
            json=scrape_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        print(f"✅ Scrape Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        
        if response.status_code == 202:
            job_id = response.json().get("job_id")
            print(f"\n📋 Job queued successfully!")
            print(f"   Job ID: {job_id}")
            
            # Check job status (optional)
            print("\n⏳ Waiting for job to complete...")
            time.sleep(10)
            
    except Exception as e:
        print(f"❌ Scrape request failed: {e}")

if __name__ == "__main__":
    test_api()
