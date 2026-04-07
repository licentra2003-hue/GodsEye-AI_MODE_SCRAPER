
import asyncio
import json
import requests
import time
from datetime import datetime

# Your Production Railway URL
PRODUCTION_URL = "https://gateway-copy-production-da60.up.railway.app"

async def test_production_query():
    scrape_endpoint = f"{PRODUCTION_URL}/api/v1/scrape"
    
    # Using the high-risk query to verify the Linux Fingerprint fix
    test_data = {
        "query": "AI tool for making consistent brand videos",
        "location": "India",
        "product_id": "b36b116e-0c19-4fa0-b669-835bd76c820e"
    }

    print(f"\n🌍 TESTING RAILWAY PRODUCTION")
    print(f"============================================================")
    print(f"Target URL: {PRODUCTION_URL}")
    print(f"Query:      {test_data['query']}")
    print(f"Started:    {datetime.now().isoformat()}")
    
    try:
        print("\nSending request to Railway...")
        response = requests.post(scrape_endpoint, json=test_data, timeout=15)
        
        if response.status_code in [200, 202]:
            job_data = response.json()
            job_id = job_data.get('job_id')
            print(f"✅ Job accepted by Railway! ID: {job_id}")
            
            print("\nPolling production result (waiting for browser launch)...")
            result_url = f"{PRODUCTION_URL}/api/job-result/{job_id}"
            
            for attempt in range(60):
                await asyncio.sleep(5)
                try:
                    res = requests.get(result_url, timeout=10)
                    data = res.json()
                    
                    status = data.get('status')
                    if status == 'completed':
                        success = data.get('data', {}).get('success')
                        if success:
                            print(f"\n🎉 SUCCESS ON RAILWAY!")
                            print(f"Result ID: {data['data'].get('job_id')}")
                            return True
                        else:
                            print(f"\n❌ PRODUCTION FAILURE: {data['data'].get('error_message')}")
                            return False
                    elif status == 'pending':
                        print(f"[{attempt+1:02d}/60] Still processing on Railway...", end='\r')
                except Exception as e:
                    print(f"\n⚠️ Connection error: {e}")
            
            print("\n⏰ Timeout: Check Railway logs.")
        else:
            print(f"\n❌ Connection Failed: {response.status_code}")
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_production_query())
