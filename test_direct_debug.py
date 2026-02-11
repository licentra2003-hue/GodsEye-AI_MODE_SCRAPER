#!/usr/bin/env python3
"""
Direct test to trigger debug screenshot in Docker
"""
import requests
import json

def direct_test():
    print("Submitting test job to trigger debug screenshot...")
    
    # Submit a simple job that should find AI Mode
    response = requests.post('http://localhost:8080/api/v1/scrape', 
                           json={'query': 'what is python', 'location': 'USA'})
    
    if response.status_code == 202:
        job_data = response.json()
        job_id = job_data['job_id']
        print(f"Job submitted: {job_id}")
        print("Waiting 30 seconds for processing...")
        
        # Wait and check result
        import time
        time.sleep(30)
        
        result_response = requests.get(f'http://localhost:8080/api/job-result/{job_id}')
        if result_response.status_code == 200:
            result = result_response.json()
            print(f"Final status: {result.get('status', 'unknown')}")
            print(f"Success: {result.get('success', False)}")
            print(f"AI Mode Found: {result.get('ai_mode_found', False)}")
        else:
            print(f"Failed to get result: {result_response.status_code}")
    else:
        print(f"Failed to submit job: {response.status_code}")

if __name__ == "__main__":
    direct_test()
