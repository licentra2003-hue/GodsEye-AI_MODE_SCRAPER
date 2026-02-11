#!/usr/bin/env python3
"""
Test script for single query submission
"""
import asyncio
import json
import requests
import time

async def test_single_query():
    """Test a single query submission"""
    
    # API endpoint
    api_url = "http://localhost:8080/api/v1/scrape"
    
    # Test query
    test_data = {
        "query": "what is artificial intelligence",
        "location": "USA"
    }
    
    print("Testing single query submission...")
    print(f"Query: {test_data['query']}")
    print(f"Location: {test_data['location']}")
    print(f"API URL: {api_url}")
    
    try:
        # Submit job
        print("\nSubmitting job...")
        response = requests.post(api_url, json=test_data, timeout=10)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 202:
            job_data = response.json()
            job_id = job_data.get('job_id')
            print(f"Job submitted successfully!")
            print(f"Job ID: {job_id}")
            
            # Poll for results
            print("\nPolling for results...")
            result_url = f"http://localhost:8080/api/job-result/{job_id}"
            
            for attempt in range(30):  # 30 attempts = 5 minutes
                await asyncio.sleep(10)  # Wait 10 seconds
                
                try:
                    result_response = requests.get(result_url, timeout=5)
                    result_data = result_response.json()
                    
                    if result_data.get('status') == 'completed':
                        print(f"\nJob completed!")
                        print(f"Results: {json.dumps(result_data, indent=2)}")
                        return True
                    elif result_data.get('status') == 'pending':
                        print(f"Attempt {attempt + 1}/30: Job still processing...")
                    else:
                        print(f"Unexpected status: {result_data.get('status')}")
                        
                except Exception as e:
                    print(f"Polling error: {e}")
                    
        else:
            print(f"Job submission failed: {response.status_code}")
            print(f"Error response: {response.text}")
            
    except Exception as e:
        print(f"Test failed: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_single_query())
