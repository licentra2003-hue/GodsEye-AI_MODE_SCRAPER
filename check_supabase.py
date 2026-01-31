import requests
import json
import os
from datetime import datetime

# Supabase configuration
SUPABASE_URL = "https://bnrpcmwkqqdmweoxkmth.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJucnBjbXdrcXFkbXdlb3hrbXRoIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MDgwMDU2NiwiZXhwIjoyMDc2Mzc2NTY2fQ.5bWehH-YMcXq-OYDamtMeplEqZuUy2xTHDieB9D8eVc"

def check_processed_jobs():
    """Check the processed_jobs table in Supabase"""
    
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        # First try to get all columns to see what's available
        url = f"{SUPABASE_URL}/rest/v1/processed_jobs?select=*&limit=5"
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 400:
            # Try to check if table exists by getting error details
            error_data = response.json() if response.content else {}
            print(f"❌ Bad Request Error: {error_data}")
            
            # Try using RPC to check table existence
            rpc_url = f"{SUPABASE_URL}/rest/v1/rpc/exec_sql"
            rpc_data = {
                "sql": "SELECT table_name FROM information_schema.tables WHERE table_name = 'processed_jobs';"
            }
            
            rpc_response = requests.post(rpc_url, headers=headers, json=rpc_data)
            if rpc_response.status_code == 200:
                tables = rpc_response.json()
                if tables:
                    print("✅ Table 'processed_jobs' exists")
                    # Now try to get count
                    count_url = f"{SUPABASE_URL}/rest/v1/rpc/exec_sql"
                    count_data = {
                        "sql": "SELECT COUNT(*) as total FROM processed_jobs;"
                    }
                    count_response = requests.post(count_url, headers=headers, json=count_data)
                    if count_response.status_code == 200:
                        count_result = count_response.json()
                        print(f"📊 Total records: {count_result[0]['total'] if count_result else 0}")
                    else:
                        print(f"❌ Could not get count: {count_response.status_code}")
                else:
                    print("❌ Table 'processed_jobs' does not exist")
            else:
                print(f"❌ Could not check table existence: {rpc_response.status_code}")
                print(f"   Response: {rpc_response.text}")
            return
        
        response.raise_for_status()
        
        jobs = response.json()
        
        # Get more detailed information
        print(f"📊 Processed Jobs Table Analysis")
        print("=" * 60)
        
        # Get total count
        count_url = f"{SUPABASE_URL}/rest/v1/processed_jobs?select=count"
        count_response = requests.get(count_url, headers=headers)
        if count_response.status_code == 200:
            count_data = count_response.json()
            total_count = count_data[0]['count'] if count_data else 0
            print(f"📈 Total records in table: {total_count}")
        
        # Get recent jobs (last 24 hours)
        recent_url = f"{SUPABASE_URL}/rest/v1/processed_jobs?select=job_id,processed_at&processed_at=gte.2026-01-24T00:00:00Z&order=processed_at.desc"
        recent_response = requests.get(recent_url, headers=headers)
        if recent_response.status_code == 200:
            recent_jobs = recent_response.json()
            print(f"🕐 Jobs processed today (last 24 hours): {len(recent_jobs)}")
            
            if recent_jobs:
                print("\nRecent jobs:")
                for i, job in enumerate(recent_jobs[:10], 1):  # Show last 10
                    job_id = job.get('job_id', 'N/A')
                    processed_at = job.get('processed_at', 'N/A')
                    try:
                        dt = datetime.fromisoformat(processed_at.replace('Z', '+00:00'))
                        formatted_time = dt.strftime('%H:%M:%S UTC')
                        hours_ago = (datetime.now(dt.tzinfo) - dt).total_seconds() / 3600
                        print(f"  {i:2d}. {job_id} - {formatted_time} ({hours_ago:.1f}h ago)")
                    except:
                        print(f"  {i:2d}. {job_id} - {processed_at}")
        
        # Check for duplicates
        all_jobs_url = f"{SUPABASE_URL}/rest/v1/processed_jobs?select=job_id"
        all_jobs_response = requests.get(all_jobs_url, headers=headers)
        if all_jobs_response.status_code == 200:
            all_jobs = all_jobs_response.json()
            job_ids = [job.get('job_id') for job in all_jobs if job.get('job_id')]
            unique_job_ids = set(job_ids)
            
            print(f"\n🔍 Deduplication Analysis:")
            print(f"   Total job entries: {len(job_ids)}")
            print(f"   Unique job IDs: {len(unique_job_ids)}")
            
            if len(job_ids) != len(unique_job_ids):
                print(f"   ⚠️  DUPLICATES FOUND!")
                duplicates = {}
                for job_id in unique_job_ids:
                    count = job_ids.count(job_id)
                    if count > 1:
                        duplicates[job_id] = count
                
                for job_id, count in duplicates.items():
                    print(f"      - {job_id}: {count} entries")
            else:
                print(f"   ✅ No duplicates - deduplication working correctly!")
        
        # Check expired records
        expired_url = f"{SUPABASE_URL}/rest/v1/processed_jobs?select=count&expires_at=lt.now()"
        expired_response = requests.get(expired_url, headers=headers)
        if expired_response.status_code == 200:
            expired_data = expired_response.json()
            expired_count = expired_data[0]['count'] if expired_data else 0
            print(f"\n⏰ Expired records (should be auto-cleaned): {expired_count}")
        
        # Check for our test jobs
        test_jobs = ["bc96aa6c-c5b8-44be-a707-5674f93dca09", "51b957e3-a2ed-44e8-b631-7089a333e852", "42db96c3-6553-47b9-96ec-f94b827c3a8c"]
        print(f"\n🧪 Test Jobs Status:")
        for test_job in test_jobs:
            test_url = f"{SUPABASE_URL}/rest/v1/processed_jobs?select=processed_at,expires_at&job_id=eq.{test_job}"
            test_response = requests.get(test_url, headers=headers)
            if test_response.status_code == 200:
                test_data = test_response.json()
                if test_data:
                    record = test_data[0]
                    processed_at = record.get('processed_at')
                    expires_at = record.get('expires_at')
                    try:
                        dt = datetime.fromisoformat(processed_at.replace('Z', '+00:00'))
                        formatted_time = dt.strftime('%Y-%m-%d %H:%M:%S UTC')
                        print(f"   ✅ {test_job}: Processed at {formatted_time}")
                    except:
                        print(f"   ✅ {test_job}: Found in table")
                else:
                    print(f"   ❌ {test_job}: Not found in table")
            else:
                print(f"   ❓ {test_job}: Could not check")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error querying Supabase: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"   Status Code: {e.response.status_code}")
            print(f"   Response: {e.response.text}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    check_processed_jobs()
