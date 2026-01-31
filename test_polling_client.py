#!/usr/bin/env python3
"""
Test client to demonstrate polling-based result retrieval
"""

import asyncio
import aiohttp
import time
from datetime import datetime

async def test_polling_results():
    """Test submitting a job and retrieving results via polling"""
    
    # Test job data
    test_job = {
        "query": "latest AI trends 2024",
        "location": "USA"
    }
    
    try:
        # Submit job via HTTP API
        print("📤 Submitting job...")
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://localhost:8080/api/v1/scrape",
                json=test_job
            ) as response:
                if response.status == 202:
                    job_data = await response.json()
                    job_id = job_data["job_id"]
                    print(f"✅ Job submitted successfully!")
                    print(f"🆔 Job ID: {job_id}")
                    print(f"🔍 Query: {test_job['query']}")
                else:
                    print(f"❌ Failed to submit job: {response.status}")
                    return
        
        # Poll for results
        print(f"\n⏳ Polling for results for job {job_id}...")
        print("📡 Checking result endpoint...")
        
        timeout = 120  # 2 minutes timeout
        start_time = time.time()
        poll_interval = 3  # Check every 3 seconds
        
        # Create new session for polling
        async with aiohttp.ClientSession() as polling_session:
            while time.time() - start_time < timeout:
                try:
                    async with polling_session.get(f"http://localhost:8080/api/job-result/{job_id}") as response:
                        if response.status == 200:
                            result_data = await response.json()
                            status = result_data.get('status')
                            
                            print(f"📊 Status: {status}")
                            
                            if status == "completed":
                                result = result_data.get('data', {})
                                print(f"\n🎉 RESULT RECEIVED!")
                                print(f"✅ Success: {result.get('success')}")
                                print(f"📊 Query: {result.get('query')}")
                                print(f"🌍 Location: {result.get('location')}")
                                
                                if result.get('ai_overview_found'):
                                    print(f"🤖 AI Overview: {result.get('ai_overview_text', '')[:100]}...")
                                
                                if result.get('source_links'):
                                    print(f"🔗 Sources found: {len(result.get('source_links', []))}")
                                
                                if result.get('error_message'):
                                    print(f"❌ Error: {result.get('error_message')}")
                                
                                print("\n✨ Test completed successfully!")
                                return
                            
                            elif status == "pending":
                                print(f"⏳ Still processing... (elapsed: {int(time.time() - start_time)}s)")
                                await asyncio.sleep(poll_interval)
                                continue
                            
                        else:
                            print(f"❌ Failed to check result: {response.status}")
                            break
                            
                except Exception as e:
                    print(f"❌ Error polling for results: {e}")
                    await asyncio.sleep(poll_interval)
                    continue
        
        print(f"⏰ Timeout after {timeout} seconds")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("🧪 Testing Polling-Based Result Retrieval")
    print("=" * 50)
    
    try:
        asyncio.run(test_polling_results())
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
