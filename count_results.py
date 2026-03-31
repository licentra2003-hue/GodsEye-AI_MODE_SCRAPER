import requests
import json

SUPABASE_URL = "https://bnrpcmwkqqdmweoxkmth.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJucnBjbXdrcXFkbXdlb3hrbXRoIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MDgwMDU2NiwiZXhwIjoyMDc2Mzc2NTY2fQ.5bWehH-YMcXq-OYDamtMeplEqZuUy2xTHDieB9D8eVc"

def count():
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Prefer": "count=exact"
    }
    
    url = f"{SUPABASE_URL}/rest/v1/product_analysis_google?select=id"
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        print(f"✅ TOTAL SUCCESSFUL ANALYSES: {len(data)}")
    else:
        print(f"❌ Error: {response.text}")

if __name__ == "__main__":
    count()
