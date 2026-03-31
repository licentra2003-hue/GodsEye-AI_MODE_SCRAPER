#!/usr/bin/env python3
"""
Test script to run 25 concurrent scraping jobs across 5 workers
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

# Create 25 queries (5 sets of 5)
TEST_QUERIES = BASE_QUERIES * 5

async def submit_single_job(session, query_data, job_index):
    try:
        async with session.post(
            f"{GATEWAY_URL}/api/v1/scrape",
            json=query_data,
            headers={"Content-Type": "application/json"}
        ) as response:
            if response.status == 202:
                result = await response.json()
                return result['job_id']
            else:
                return None
    except:
        return None

async def main():
    print("🚀 25-QUERY TEST: Scaled Concurrency (5 Workers × 5 Tabs)")
    print("=" * 60)
    print(f"🕒 Started at: {datetime.now().isoformat()}")
    
    # Submit 25 jobs concurrently
    async with aiohttp.ClientSession() as session:
        start_time = time.time()
        tasks = [submit_single_job(session, q, i) for i, q in enumerate(TEST_QUERIES)]
        job_ids = await asyncio.gather(*tasks)
        
        success_count = len([jid for jid in job_ids if jid])
        print(f"\n📊 SUBMISSION COMPLETE:")
        print(f"   Success: {success_count}/25")
        print(f"   Submission duration: {time.time() - start_time:.2f}s")
        print("-" * 60)
        print("⏳ Monitor logs: 'docker logs godseye-googleaimodescraper-worker_node-1 -f'")
        print("-" * 60)

if __name__ == "__main__":
    asyncio.run(main())
