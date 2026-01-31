#!/usr/bin/env python3
"""
Test script to verify deduplication fix
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime

# API Gateway configuration
GATEWAY_URL = "http://localhost:8080"

# Test query
TEST_QUERY = {
    "query": "deduplication test query",
    "location": "USA"
}

async def submit_single_job(session, query_data):
    """Submit a single scraping job"""
    start_time = time.time()
    
    try:
        async with session.post(
            f"{GATEWAY_URL}/api/v1/scrape",
            json=query_data,
            headers={"Content-Type": "application/json"}
        ) as response:
            if response.status == 202:
                result = await response.json()
                end_time = time.time()
                
                print(f"✅ Job submitted successfully!")
                print(f"   Query: '{query_data['query']}'")
                print(f"   Location: {query_data['location']}")
                print(f"   Job ID: {result['job_id']}")
                print(f"   Status: {result['status']}")
                print(f"   Submission time: {end_time - start_time:.2f}s")
                
                return result['job_id']
            else:
                error_text = await response.text()
                print(f"❌ Job submission failed!")
                print(f"   Status Code: {response.status}")
                print(f"   Error: {error_text}")
                return None
                
    except Exception as e:
        print(f"❌ Job submission error!")
        print(f"   Error: {str(e)}")
        return None

async def main():
    """Main function to test deduplication"""
    print("🧪 Testing Job Deduplication Fix")
    print("=" * 50)
    print(f"📅 Test started at: {datetime.now().isoformat()}")
    print(f"🎯 Testing single query to verify deduplication")
    print("=" * 50)
    
    # Check API Gateway health first
    print("1️⃣ Checking API Gateway health...")
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{GATEWAY_URL}/health") as response:
                if response.status == 200:
                    health_data = await response.json()
                    print(f"✅ Gateway Status: {health_data.get('status', 'unknown')}")
                    print(f"   RabbitMQ: {health_data.get('rabbitmq', 'unknown')}")
                else:
                    print(f"❌ Gateway health check failed: {response.status}")
                    return
        except Exception as e:
            print(f"❌ Cannot connect to API Gateway: {e}")
            return
    
    print("\n2️⃣ Submitting test job...")
    print("-" * 50)
    
    # Submit test job
    async with aiohttp.ClientSession() as session:
        job_id = await submit_single_job(session, TEST_QUERY)
        
        if job_id:
            print(f"\n✅ Test job submitted successfully!")
            print(f"   Job ID: {job_id}")
            print(f"\n📝 Monitor worker logs to see:")
            print(f"   - Job should be processed only once")
            print(f"   - No duplicate processing messages")
            print(f"   - Proper acknowledgment")
            print(f"\n🔍 Use this command to monitor:")
            print(f"   docker logs godseye-googleaimodescraper-worker_node-1 --follow")
        else:
            print(f"\n❌ Test failed!")
        
        print(f"\n✅ Test completed at: {datetime.now().isoformat()}")

if __name__ == "__main__":
    asyncio.run(main())
