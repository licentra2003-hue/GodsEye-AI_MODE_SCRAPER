#!/usr/bin/env python3
"""
Test script for local testing with HEADLESS=false
"""
import asyncio
import json
import requests
import time

async def test_local_server():
    """Test the local server with HEADLESS=false setup"""
    
    # API endpoint
    api_url = "http://localhost:8080/api/v1/scrape"
    
    # Test query
    test_data = {
        "query": "what is artificial intelligence",
        "location": "USA"
    }
    
    print("=== LOCAL SERVER TEST ===")
    print("Testing HEADLESS=false setup without Docker")
    print(f"Query: {test_data['query']}")
    print(f"Location: {test_data['location']}")
    print(f"API URL: {api_url}")
    print()
    
    try:
        # Step 1: Check server health
        print("1. Checking server health...")
        health_response = requests.get("http://localhost:8080/health", timeout=5)
        print(f"   Health Status: {health_response.status_code}")
        print(f"   Health Response: {health_response.json()}")
        print()
        
        # Step 2: Submit job
        print("2. Submitting job...")
        response = requests.post(api_url, json=test_data, timeout=10)
        
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.text}")
        print()
        
        if response.status_code in [200, 202]:
            job_data = response.json()
            job_id = job_data.get('job_id')
            print(f"   Job submitted successfully!")
            print(f"   Job ID: {job_id}")
            print()
            
            # Step 3: Poll for results
            print("3. Polling for results...")
            result_url = f"http://localhost:8080/api/job-result/{job_id}"
            
            for attempt in range(10):  # 10 attempts = 50 seconds
                await asyncio.sleep(5)  # Wait 5 seconds
                
                try:
                    result_response = requests.get(result_url, timeout=5)
                    result_data = result_response.json()
                    
                    print(f"   Attempt {attempt + 1}/10: Status = {result_data.get('status')}")
                    
                    if result_data.get('status') == 'completed':
                        print(f"\n   Job completed successfully!")
                        print(f"   AI Mode Found: {result_data.get('ai_mode_found')}")
                        print(f"   AI Mode Text: {result_data.get('ai_mode_text')}")
                        print(f"   Sources Count: {len(result_data.get('source_links', []))}")
                        print(f"   Full Results: {json.dumps(result_data, indent=6)}")
                        return True
                    elif result_data.get('status') == 'failed':
                        print(f"   Job failed: {result_data.get('error_message')}")
                        return False
                        
                except Exception as e:
                    print(f"   Polling error: {e}")
                    
            print(f"\n   Job timed out after 50 seconds")
            return False
        else:
            print(f"   Job submission failed: {response.status_code}")
            print(f"   Error response: {response.text}")
            return False
            
    except Exception as e:
        print(f"Test failed: {e}")
        return False

if __name__ == "__main__":
    print("Starting local server test...")
    print("This test simulates the API flow without Docker/RabbitMQ")
    print("You can observe the workflow in the server logs")
    print()
    
    success = asyncio.run(test_local_server())
    
    print("\n=== TEST RESULTS ===")
    if success:
        print("SUCCESS: Local server test completed")
        print("Ready to test with actual worker and HEADLESS=false")
    else:
        print("FAILED: Local server test failed")
        print("Check server logs for details")
