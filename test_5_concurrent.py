
import requests
import json
import time
from datetime import datetime

GATEWAY_URL = "http://localhost:8080/api/v1/scrape"

QUERIES = [
    "AI tool for making consistent brand videos",
    "easy video creator for social media marketing",
    "generate short marketing videos with AI visuals",
    "how to generate professional videos without editing skills",
    "software to quickly produce engaging video content"
]

def run_test():
    VALID_PRODUCT_ID = "b36b116e-0c19-4fa0-b669-835bd76c820e"
    print(f"\n5-QUERY TEST: Video Marketing Queries")
    print(f"============================================================")
    print(f"Started at: {datetime.now().isoformat()}")

    for i, query in enumerate(QUERIES):
        payload = {
            "query": query,
            "product_id": VALID_PRODUCT_ID,
            "location": "India"
        }
        try:
            resp = requests.post(GATEWAY_URL, json=payload, timeout=5)
            # 202 is the success code (StatusAccepted)
            if resp.status_code in [200, 202]:
                data = resp.json()
                print(f"[OK] [{i+1:05d}/05] Submitted: {query} (Job ID: {data.get('job_id')})")
            else:
                print(f"[ERROR] [{i+1:05d}/05] Failed ({resp.status_code}): {resp.text}")
        except Exception as e:
            print(f"[ERROR] [{i+1:05d}/05] Error submitting: {str(e)}")
        
        # Tiny delay to prevent slamming the gateway
        time.sleep(0.1)

    print(f"\nSUBMISSION COMPLETE:")
    print(f"Check logs with 'docker-compose logs -f'")
    print(f"----------------------------------------------------\n")

if __name__ == "__main__":
    run_test()
