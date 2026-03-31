#!/usr/bin/env python3
"""
Test script to run 50 concurrent scraping jobs across 20 workers
(Each worker handles batches of 5 queries in 1 browser)
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime
import uuid

# API Gateway configuration
GATEWAY_URL = "http://localhost:8080"
VALID_PRODUCT_ID = "b36b116e-0c19-4fa0-b669-835bd76c820e"

# Base test queries - 5 different queries
BASE_QUERIES = [
    {
        "query": "best mobile app development frameworks 2024",
        "location": "India",
        "product_id": VALID_PRODUCT_ID
    },
    {
        "query": "Best MMP Platforms in India",
        "location": "India",
        "product_id": VALID_PRODUCT_ID
    },
    {
        "query": "artificial intelligence tools for business",
        "location": "India",
        "product_id": VALID_PRODUCT_ID
    },
    {
        "query": "cybersecurity best practices 2024",
        "location": "India",
        "product_id": VALID_PRODUCT_ID
    },
    {
        "query": "blockchain technology use cases",
        "location": "India",
        "product_id": VALID_PRODUCT_ID
    }
]

# Create 50 queries (10 sets of 5)
TEST_QUERIES = BASE_QUERIES * 10

async def submit_single_job(session, query_data, job_index):
    """Submit a single scraping job"""
    try:
        async with session.post(
            f"{GATEWAY_URL}/api/v1/scrape",
            json=query_data,
            headers={"Content-Type": "application/json"}
        ) as response:
            if response.status == 202:
                result = await response.json()
                # print(f"✅ Job {job_index + 1} submitted: {result['job_id']}")
                return result['job_id']
            else:
                error_text = await response.text()
                print(f"❌ Job {job_index + 1} failed: {error_text}")
                return None
    except Exception as e:
        print(f"❌ Submission error for Job {job_index + 1}: {e}")
        return None

async def main():
    print("🚀 LOAD TEST: Submitting 50 Concurrent Scraping Jobs")
    print("=" * 60)
    print(f"⚙️  Architecture: 20 Workers (Batch Size 5)")
    print(f"🕒 Started at: {datetime.now().isoformat()}")
    print("=" * 60)
    
    # Check Gateway Health
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{GATEWAY_URL}/health") as r:
                if r.status != 200:
                    print("❌ Gateway not ready! Please wait for 'docker-compose up' to settle.")
                    return
        except:
            print("❌ Gateway unreachable! Check if API Gateway is running.")
            return

    # Submit 50 jobs concurrently
    async with aiohttp.ClientSession() as session:
        start_time = time.time()
        tasks = [submit_single_job(session, q, i) for i, q in enumerate(TEST_QUERIES)]
        job_ids = await asyncio.gather(*tasks)
        
        success_count = len([jid for jid in job_ids if jid])
        print(f"\n📊 SUBMISSION COMPLETE:")
        print(f"   Success: {success_count}/50")
        print(f"   Time Taken: {time.time() - start_time:.2f}s")
        print("-" * 60)
        print(f"⏳ Monitoring tip: Run 'docker logs godseye-googleaimodescraper-worker_node-1 -f'")
        print(f"📝 RESULTS: Check Supabase 'product_analysis_google' table soon")
        print("-" * 60)

if __name__ == "__main__":
    asyncio.run(main())
