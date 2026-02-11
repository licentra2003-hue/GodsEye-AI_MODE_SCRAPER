#!/usr/bin/env python3
"""
Quick test to trigger debug screenshots
"""
import requests
import time

def test_screenshot():
    print("Testing debug screenshot functionality...")
    
    # Submit job
    response = requests.post('http://localhost:8080/api/v1/scrape', 
                           json={'query': 'what is python programming', 'location': 'USA'})
    
    if response.status_code == 202:
        job_data = response.json()
        job_id = job_data['job_id']
        print(f"Job submitted: {job_id}")
        
        # Wait for completion
        for i in range(30):
            result_response = requests.get(f'http://localhost:8080/api/job-result/{job_id}')
            result = result_response.json()
            status = result.get('status', 'unknown')
            print(f"Status: {status}")
            
            if status == 'completed':
                print("Job completed!")
                print(f"Success: {result.get('success', False)}")
                print(f"AI Mode Found: {result.get('ai_mode_found', False)}")
                break
            time.sleep(2)
    else:
        print(f"Failed to submit job: {response.status_code}")

if __name__ == "__main__":
    test_screenshot()
