
import asyncio
import json
import requests
import sys
import argparse
from datetime import datetime

async def test_single_query(query, location="India", product_id=None):
    api_url = "http://localhost:8080/api/v1/scrape"
    
    test_data = {
        "query": query,
        "location": location
    }
    if product_id:
        test_data["product_id"] = product_id

    print(f"\n🚀 STARTING SINGLE QUERY TEST")
    print(f"============================================================")
    print(f"Query:    {query}")
    print(f"Location: {location}")
    print(f"Started:  {datetime.now().isoformat()}")
    
    try:
        print("\nSubmitting job to Gateway...")
        response = requests.post(api_url, json=test_data, timeout=10)
        
        if response.status_code in [200, 202]:
            job_data = response.json()
            job_id = job_data.get('job_id')
            print(f"✅ Job queued! ID: {job_id}")
            
            print("\nPolling for result (this can take ~60-90s)...")
            result_url = f"http://localhost:8080/api/job-result/{job_id}"
            
            # 60 attempts * 5 seconds = 5 minutes total polling
            for attempt in range(60):
                await asyncio.sleep(5)
                
                try:
                    result_response = requests.get(result_url, timeout=5)
                    result_data = result_response.json()
                    
                    status = result_data.get('status')
                    if status == 'completed':
                        success = result_data.get('data', {}).get('success')
                        if success:
                            print(f"\n🎉 SUCCESS! Result found.")
                            print(f"Query Ref: {result_data['data']['query']}")
                            return True
                        else:
                            print(f"\n❌ JOB FAILED: {result_data['data'].get('error_message')}")
                            return False
                    elif status == 'pending':
                        print(f"[{attempt+1:02d}/60] Processing...", end='\r')
                    else:
                        print(f"\n⚠️ Unexpected status: {status}")
                except Exception as e:
                    print(f"\n⚠️ Polling error: {e}")
            
            print("\n⏰ Polling timed out (5 minutes). Check worker logs.")
        else:
            print(f"\n❌ Job submission failed: {response.status_code}")
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", default="AI tool for making consistent brand videos")
    parser.add_argument("--location", default="India")
    parser.add_argument("--product_id", default="b36b116e-0c19-4fa0-b669-835bd76c820e")
    args = parser.parse_args()
    
    asyncio.run(test_single_query(args.query, args.location, args.product_id))
