#!/usr/bin/env python3
"""
Check job status by monitoring the worker
"""

import subprocess
import time
import requests

def check_job_status():
    """Check if there are any jobs being processed"""
    print("🔍 Checking job status...")
    
    # Check RabbitMQ queues
    try:
        response = requests.get(
            "http://localhost:15672/api/queues/%2F/scrape_jobs",
            auth=("admin", "admin123")
        )
        if response.status_code == 200:
            queue_data = response.json()
            messages = queue_data.get("messages", 0)
            print(f"📊 Queue status: {messages} messages in queue")
            
            if messages > 0:
                print("⏳ Jobs are waiting to be processed")
            else:
                print("✅ Queue is empty")
    except Exception as e:
        print(f"❌ Error checking queue: {e}")
    
    # Test another scrape to see if worker processes it
    print("\n🧪 Submitting new job...")
    try:
        scrape_data = {
            "query": "python web scraping",
            "location": "United States"
        }
        response = requests.post(
            "http://localhost:8080/api/v1/scrape",
            json=scrape_data
        )
        if response.status_code == 202:
            job_id = response.json().get('job_id')
            print(f"✅ Job submitted: {job_id}")
            
            # Check queue again
            time.sleep(1)
            response = requests.get(
                "http://localhost:15672/api/queues/%2F/scrape_jobs",
                auth=("admin", "admin123")
            )
            if response.status_code == 200:
                queue_data = response.json()
                messages = queue_data.get("messages", 0)
                print(f"📊 Queue status after submission: {messages} messages")
                
                # Wait a bit and check again
                print("⏳ Waiting for worker to process...")
                time.sleep(5)
                
                response = requests.get(
                    "http://localhost:15672/api/queues/%2F/scrape_jobs",
                    auth=("admin", "admin123")
                )
                if response.status_code == 200:
                    queue_data = response.json()
                    messages = queue_data.get("messages", 0)
                    print(f"📊 Queue status after 5 seconds: {messages} messages")
                    
                    if messages == 0:
                        print("✅ Worker processed the job successfully!")
                    else:
                        print("⚠ Worker might not be processing jobs")
    except Exception as e:
        print(f"❌ Error submitting job: {e}")

if __name__ == "__main__":
    check_job_status()
