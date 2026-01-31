#!/usr/bin/env python3
"""
Test client to demonstrate WebSocket result reception
"""

import asyncio
import websockets
import json
import aiohttp
import time
from datetime import datetime

async def test_websocket_results():
    """Test submitting a job and receiving results via WebSocket"""
    
    # Test job data
    test_job = {
        "query": "latest AI trends 2024",
        "location": "United States"
    }
    
    # WebSocket connection
    ws_uri = "ws://localhost:8080/ws/job-results"
    
    try:
        # Connect to WebSocket
        print("🔌 Connecting to WebSocket...")
        async with websockets.connect(ws_uri) as websocket:
            print("✅ WebSocket connected!")
            
            # Listen for welcome message
            welcome_msg = await websocket.recv()
            welcome_data = json.loads(welcome_msg)
            print(f"📥 Welcome message: {welcome_data}")
            
            # Submit job via HTTP API
            print("\n📤 Submitting job...")
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
            
            # Wait for results
            print(f"\n⏳ Waiting for results for job {job_id}...")
            print("📡 Listening for WebSocket messages...")
            
            timeout = 120  # 2 minutes timeout
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                try:
                    # Wait for message with timeout
                    message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    data = json.loads(message)
                    
                    print(f"\n📥 WebSocket Message:")
                    print(f"   Type: {data.get('type')}")
                    print(f"   Timestamp: {data.get('timestamp')}")
                    
                    if data.get('type') == 'job_result':
                        result_data = data.get('data', {})
                        result_job_id = result_data.get('job_id')
                        
                        if result_job_id == job_id:
                            print(f"🎉 RESULT RECEIVED FOR JOB {job_id}!")
                            print(f"✅ Success: {result_data.get('success')}")
                            print(f"📊 Query: {result_data.get('query')}")
                            print(f"🌍 Location: {result_data.get('location')}")
                            
                            if result_data.get('ai_overview_found'):
                                print(f"🤖 AI Overview: {result_data.get('ai_overview_text', '')[:100]}...")
                            
                            if result_data.get('source_links'):
                                print(f"🔗 Sources found: {len(result_data.get('source_links', []))}")
                            
                            if result_data.get('error_message'):
                                print(f"❌ Error: {result_data.get('error_message')}")
                            
                            print("\n✨ Test completed successfully!")
                            return
                        else:
                            print(f"ℹ️ Result for different job: {result_job_id}")
                    
                except asyncio.TimeoutError:
                    print("⏰ No message received in last 5 seconds, still waiting...")
                    continue
                except websockets.exceptions.ConnectionClosed:
                    print("❌ WebSocket connection closed")
                    return
            
            print(f"⏰ Timeout after {timeout} seconds")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("🧪 Testing WebSocket Result Reception")
    print("=" * 50)
    
    try:
        asyncio.run(test_websocket_results())
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
