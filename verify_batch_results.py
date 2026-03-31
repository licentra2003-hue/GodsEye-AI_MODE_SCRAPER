import requests
import json
from datetime import datetime

# Supabase configuration
SUPABASE_URL = "https://bnrpcmwkqqdmweoxkmth.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJucnBjbXdrcXFkbXdlb3hrbXRoIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MDgwMDU2NiwiZXhwIjoyMDc2Mzc2NTY2fQ.5bWehH-YMcXq-OYDamtMeplEqZuUy2xTHDieB9D8eVc"

def verify_results():
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    
    print("🔍 Fetching latest entries from 'product_analysis_google'...")
    
    # Get last 10 entries ordered by created_at desc
    url = f"{SUPABASE_URL}/rest/v1/product_analysis_google?select=id,product_id,search_query,created_at&order=created_at.desc&limit=10"
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        results = response.json()
        
        if not results:
            print("❌ No results found in the table.")
            return

        print(f"✅ Found {len(results)} recent records:")
        print("=" * 80)
        print(f"{'ID':<40} | {'Product ID':<40} | {'Search Query':<30}")
        print("-" * 115)
        
        for r in results:
            print(f"{r.get('id', 'N/A'):<40} | {r.get('product_id', 'N/A'):<40} | {r.get('search_query', 'N/A'):<30}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    verify_results()
