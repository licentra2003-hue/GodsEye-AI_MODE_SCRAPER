#!/usr/bin/env python3
"""
Track 5 frontend queries every 10 seconds
"""
import subprocess
import json
import time
from datetime import datetime
import re

def get_gateway_logs(since_minutes=1):
    """Get recent gateway logs"""
    try:
        result = subprocess.run(
            ['docker', 'logs', 'godseye-gateway', f'--since={since_minutes}m'],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.stdout
    except:
        return ""

def extract_job_info(logs):
    """Extract job information from logs"""
    jobs = {}
    
    # Find job submissions
    queued_jobs = re.findall(r'📋 Job ([a-f0-9-]+) queued for query: ([^\n]+)', logs)
    for job_id, query in queued_jobs:
        jobs[job_id] = {
            'status': 'queued',
            'query': query.strip(),
            'timestamp': datetime.now().strftime('%H:%M:%S')
        }
    
    # Find job completions
    completed_jobs = re.findall(r'💾 Result stored for job ([a-f0-9-]+)', logs)
    for job_id in completed_jobs:
        if job_id in jobs:
            jobs[job_id]['status'] = 'completed'
    
    # Find job results
    result_jobs = re.findall(r'📋 Job ([a-f0-9-]+) result received: ([^\n]+)', logs)
    for job_id, query in result_jobs:
        if job_id not in jobs:
            jobs[job_id] = {
                'status': 'processing',
                'query': query.strip(),
                'timestamp': datetime.now().strftime('%H:%M:%S')
            }
    
    return jobs

def track_queries():
    """Track the 5 frontend queries"""
    print("🔍 Tracking 5 Frontend Queries - Started at", datetime.now().strftime('%H:%M:%S'))
    print("=" * 80)
    
    tracked_jobs = {}
    poll_count = 0
    
    while poll_count < 60:  # Track for 10 minutes (60 * 10 seconds)
        logs = get_gateway_logs(2)  # Get last 2 minutes of logs
        current_jobs = extract_job_info(logs)
        
        # Update tracked jobs
        for job_id, info in current_jobs.items():
            if job_id not in tracked_jobs:
                tracked_jobs[job_id] = info
                print(f"\n🆕 NEW JOB: {job_id[:8]}...")
                print(f"   Query: {info['query'][:60]}...")
                print(f"   Status: {info['status']}")
            elif tracked_jobs[job_id]['status'] != info['status']:
                tracked_jobs[job_id]['status'] = info['status']
                print(f"\n✅ UPDATE: {job_id[:8]}... -> {info['status'].upper()}")
        
        # Display current status
        if poll_count % 6 == 0:  # Every minute
            print(f"\n⏰ {datetime.now().strftime('%H:%M:%S')} - Status Update:")
            print(f"   Total Jobs Tracked: {len(tracked_jobs)}")
            
            status_count = {'queued': 0, 'processing': 0, 'completed': 0}
            for job in tracked_jobs.values():
                status_count[job['status']] += 1
            
            print(f"   Queued: {status_count['queued']} | Processing: {status_count['processing']} | Completed: {status_count['completed']}")
            
            # Show completed jobs
            if status_count['completed'] > 0:
                print("\n🎉 Completed Jobs:")
                for job_id, job in tracked_jobs.items():
                    if job['status'] == 'completed':
                        print(f"   ✅ {job_id[:8]}... - {job['query'][:50]}...")
        
        poll_count += 1
        time.sleep(10)
    
    print("\n" + "=" * 80)
    print("📊 FINAL SUMMARY:")
    print(f"Total Jobs Tracked: {len(tracked_jobs)}")
    
    for job_id, job in tracked_jobs.items():
        status_emoji = {'queued': '⏳', 'processing': '🔄', 'completed': '✅'}
        print(f"{status_emoji.get(job['status'], '❓')} {job_id[:8]}... - {job['status'].upper()}")
        print(f"   Query: {job['query']}")

if __name__ == "__main__":
    track_queries()
