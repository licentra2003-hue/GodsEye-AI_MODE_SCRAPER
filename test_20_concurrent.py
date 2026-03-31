
import requests
import json
import time
from datetime import datetime

GATEWAY_URL = "http://localhost:8080/api/v1/scrape"

QUERIES = [
    "future of artificial intelligence in healthcare",
    "best practices for remote software engineering teams",
    "impact of climate change on agriculture in asia",
    "blockchain technology use cases in supply chain",
    "quantum computing vs classical computing explained",
    "top 10 travel destinations in europe for 2025",
    "how to learn web development in 6 months",
    "sustainable energy solutions for urban cities",
    "cybersecurity threats in the age of IoT",
    "history of the internet and its evolution",
    "machine learning applications in financial services",
    "ethics of genetic engineering in humans",
    "rise of electric vehicles and its impact on oil",
    "space exploration milestones in the last decade",
    "mental health awareness in the workplace",
    "benefits of a plant-based diet for longevity",
    "future of work and the role of automation",
    "impact of social media on teenage psychology",
    "modern architecture trends in sustainable design",
    "history of ancient civilizations in south america"
]

def run_test():
    VALID_PRODUCT_ID = "b36b116e-0c19-4fa0-b669-835bd76c820e"
    print(f"\n20-QUERY TEST: Scaled Concurrency (5 Workers x 4 Tabs)")
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
                print(f"[OK] [{i+1:02d}/20] Submitted: {query} (Job ID: {data.get('job_id')})")
            else:
                print(f"[ERROR] [{i+1:02d}/20] Failed ({resp.status_code}): {resp.text}")
        except Exception as e:
            print(f"[ERROR] [{i+1:02d}/20] Error submitting: {str(e)}")
        
        # Tiny delay to prevent slamming the gateway
        time.sleep(0.1)

    print(f"\nSUBMISSION COMPLETE:")
    print(f"Check logs with 'docker-compose logs -f'")
    print(f"----------------------------------------------------\n")

if __name__ == "__main__":
    run_test()
