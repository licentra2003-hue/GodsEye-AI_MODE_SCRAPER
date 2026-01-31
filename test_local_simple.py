#!/usr/bin/env python3
"""
Simple local test for GodsEye services
"""

import subprocess
import sys
import time
import requests
import os
from pathlib import Path

def test_rabbitmq():
    """Test RabbitMQ connection"""
    print("🐰 Testing RabbitMQ...")
    try:
        response = requests.get(
            "http://localhost:15672/api/overview",
            auth=("admin", "admin123"),
            timeout=5
        )
        if response.status_code == 200:
            print("✅ RabbitMQ is running")
            return True
    except:
        pass
    
    print("❌ RabbitMQ is not running")
    return False

def test_gateway():
    """Test Gateway health"""
    print("🌐 Testing Gateway...")
    try:
        response = requests.get("http://localhost:8080/health", timeout=5)
        if response.status_code == 200:
            print("✅ Gateway is running")
            print(f"   Response: {response.json()}")
            return True
    except:
        pass
    
    print("❌ Gateway is not running")
    return False

def test_scrape():
    """Test scrape endpoint"""
    print("🧪 Testing Scrape Endpoint...")
    try:
        scrape_data = {
            "query": "best mmps platform",
            "location": "India"
        }
        response = requests.post(
            "http://localhost:8080/api/v1/scrape",
            json=scrape_data,
            timeout=5
        )
        if response.status_code == 202:
            print("✅ Scrape request successful")
            print(f"   Job ID: {response.json().get('job_id')}")
            return True
        else:
            print(f"❌ Scrape request failed: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"❌ Scrape request error: {e}")
    
    return False

def start_gateway():
    """Start the Gateway in a new window"""
    print("🚀 Starting Gateway...")
    if sys.platform == "win32":
        # Use start command to open in new window
        subprocess.Popen(
            ["start", "cmd", "/k", "cd gateway && go run main.go"],
            shell=True,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
    else:
        # Use gnome-terminal or xterm
        subprocess.Popen(
            ["gnome-terminal", "--", "bash", "-c", "cd gateway && go run main.go"],
            cwd=os.path.dirname(os.path.abspath(__file__))
        )

def start_worker():
    """Start the Worker in a new window"""
    print("🚀 Starting Worker...")
    if sys.platform == "win32":
        # Use start command to open in new window
        subprocess.Popen(
            ["start", "cmd", "/k", "cd worker && python worker_main.py"],
            shell=True,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
    else:
        # Use gnome-terminal or xterm
        subprocess.Popen(
            ["gnome-terminal", "--", "bash", "-c", "cd worker && python worker_main.py"],
            cwd=os.path.dirname(os.path.abspath(__file__))
        )

def main():
    """Main test function"""
    print("🚀 GodsEye Simple Local Test")
    print("=" * 40)
    
    # Test RabbitMQ
    if not test_rabbitmq():
        print("\n❌ Please start RabbitMQ first:")
        print("   docker run -d --name godseye-rabbitmq-local -p 5672:5672 -p 15672:15672 -e RABBITMQ_DEFAULT_USER=admin -e RABBITMQ_DEFAULT_PASS=admin123 rabbitmq:3.12-management-alpine")
        return
    
    # Test Gateway
    if not test_gateway():
        print("\n🚀 Starting Gateway...")
        start_gateway()
        print("⏳ Waiting for Gateway to start...")
        
        # Wait for gateway to start
        for i in range(30):
            time.sleep(1)
            if test_gateway():
                break
        else:
            print("❌ Gateway failed to start")
            return
    
    # Test Worker (we can't easily test it, but we can test the scrape endpoint)
    print("\n🚀 Starting Worker...")
    start_worker()
    print("⏳ Waiting for Worker to connect...")
    time.sleep(3)
    
    # Test scrape endpoint
    if test_scrape():
        print("\n✅ All tests passed!")
        print("\n📊 Services running:")
        print("   - RabbitMQ: http://localhost:15672 (admin/admin123)")
        print("   - Gateway: http://localhost:8080")
        print("   - Worker: Running in separate window")
    else:
        print("\n❌ Some tests failed")
        print("\n🔍 Check the separate terminal windows for errors")

if __name__ == "__main__":
    main()
