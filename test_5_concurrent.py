#!/usr/bin/env python3
"""
Test script to run 5 concurrent scraping jobs with Supabase storage
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime
import uuid

# API Gateway configuration
GATEWAY_URL = "http://localhost:8080"

# Test queries - 5 different queries
TEST_QUERIES = [
    {
        "query": "best mobile app development frameworks 2024",
        "location": "India",
        "product_id": "b36b116e-0c19-4fa0-b669-835bd76c820e"
    },
    {
        "query": "Best MMP Platforms in India",
        "location": "India",
        "product_id": "b36b116e-0c19-4fa0-b669-835bd76c820e"
    },
    {
        "query": "artificial intelligence tools for business",
        "location": "India",
        "product_id": "b36b116e-0c19-4fa0-b669-835bd76c820e"
    },
    {
        "query": "cybersecurity best practices 2024",
        "location": "India",
        "product_id": "b36b116e-0c19-4fa0-b669-835bd76c820e"
    },
    {
        "query": "blockchain technology use cases",
        "location": "India",
        "product_id": "b36b116e-0c19-4fa0-b669-835bd76c820e"
    }
]

async def submit_single_job(session, query_data, job_index):
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
                
                print(f"✅ Job {job_index + 1} submitted successfully!")
                print(f"   Query: '{query_data['query']}'")
                print(f"   Location: {query_data['location']}")
                print(f"   Job ID: {result['job_id']}")
                print(f"   Status: {result['status']}")
                print(f"   Submission time: {end_time - start_time:.2f}s")
                print("-" * 60)
                
                return {
                    "index": job_index + 1,
                    "job_id": result['job_id'],
                    "query": query_data['query'],
                    "location": query_data['location'],
                    "status": result['status'],
                    "submission_time": end_time - start_time,
                    "submitted_at": datetime.now().isoformat()
                }
            else:
                error_text = await response.text()
                print(f"❌ Job {job_index + 1} submission failed!")
                print(f"   Query: '{query_data['query']}'")
                print(f"   Status Code: {response.status}")
                print(f"   Error: {error_text}")
                print("-" * 60)
                
                return None
                
    except Exception as e:
        print(f"❌ Job {job_index + 1} submission error!")
        print(f"   Query: '{query_data['query']}'")
        print(f"   Error: {str(e)}")
        print("-" * 60)
        
        return None

async def check_job_status(session, job_id, job_index):
    """Check the status of a specific job"""
    try:
        async with session.get(
            f"{GATEWAY_URL}/health"
        ) as response:
            if response.status == 200:
                # For now, we'll just check if the gateway is healthy
                # In a real scenario, you might want to implement a job status endpoint
                return {"job_id": job_id, "status": "processing"}
    except:
        pass
    
    return {"job_id": job_id, "status": "unknown"}

async def main():
    """Main function to run concurrent tests"""
    print("🧪 Testing 5 Concurrent Scraping Jobs (Supabase Mode)")
    print("=" * 60)
    print(f"📅 Test started at: {datetime.now().isoformat()}")
    print(f"🎯 Total queries: {len(TEST_QUERIES)}")
    print(f"💾 Storage Mode: Supabase")
    print("=" * 60)
    
    # Check API Gateway health first
    print("1️⃣ Checking API Gateway health...")
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{GATEWAY_URL}/health") as response:
                if response.status == 200:
                    health_data = await response.json()
                    print(f"✅ Gateway Status: {health_data.get('status', 'unknown')}")
                    print(f"   RabbitMQ: {health_data.get('rabbitmq', 'unknown')}")
                    print(f"   Version: {health_data.get('version', 'unknown')}")
                else:
                    print(f"❌ Gateway health check failed: {response.status}")
                    return
        except Exception as e:
            print(f"❌ Cannot connect to API Gateway: {e}")
            return
    
    print("\n2️⃣ Submitting 5 concurrent jobs...")
    print("-" * 60)
    
    # Submit all jobs concurrently
    async with aiohttp.ClientSession() as session:
        # Create tasks for all job submissions
        tasks = []
        for i, query_data in enumerate(TEST_QUERIES):
            task = asyncio.create_task(submit_single_job(session, query_data, i))
            tasks.append(task)
        
        # Wait for all submissions to complete
        submitted_jobs = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter successful submissions
        successful_jobs = [job for job in submitted_jobs if job is not None]
        
        print(f"\n📊 Submission Summary:")
        print(f"   Total attempted: {len(TEST_QUERIES)}")
        print(f"   Successful: {len(successful_jobs)}")
        print(f"   Failed: {len(TEST_QUERIES) - len(successful_jobs)}")
        
        if successful_jobs:
            avg_submission_time = sum(job['submission_time'] for job in successful_jobs) / len(successful_jobs)
            print(f"   Average submission time: {avg_submission_time:.2f}s")
        
        print("\n3️⃣ Job IDs submitted:")
        for job in successful_jobs:
            print(f"   Job {job['index']}: {job['job_id']} ({job['query'][:50]}...)")
        
        print(f"\n⏳ Jobs are now being processed by workers...")
        print(f"📝 Check Supabase table 'product_analysis_google' for results")
        print(f"🔍 Use Docker logs to monitor worker processing:")
        print(f"   docker logs godseye-googleaimodescraper-worker_node-1 --follow")
        print(f"   docker logs godseye-googleaimodescraper-worker_node-2 --follow")
        print(f"   docker logs godseye-googleaimodescraper-worker_node-3 --follow")
        
        print(f"\n✅ Test completed at: {datetime.now().isoformat()}")

if __name__ == "__main__":
    asyncio.run(main())
