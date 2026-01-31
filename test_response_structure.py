import requests
import json

def test_api_response():
    """Test the actual API response structure"""
    
    # Submit a job
    job_data = {
        "query": "latest AI trends 2024",
        "location": "USA"
    }
    
    print("📤 Submitting job...")
    response = requests.post("http://localhost:8080/api/v1/scrape", 
                           json=job_data)
    
    if response.status_code in [200, 202]:
        result = response.json()
        job_id = result.get('job_id')
        print(f"✅ Job submitted: {job_id}")
        
        # Poll for results
        print("⏳ Polling for results...")
        import time
        for i in range(20):  # Try for 2 minutes
            time.sleep(6)
            
            result_response = requests.get(f"http://localhost:8080/api/job-result/{job_id}")
            
            if result_response.status_code == 200:
                result_data = result_response.json()
                print(f"📊 Poll {i+1}: Status = {result_data.get('status')}")
                
                if result_data.get('status') == 'completed':
                    print("🎉 Job completed!")
                    print(f"📋 Response structure:")
                    print(json.dumps(result_data, indent=2))
                    
                    # Check if data is empty
                    if 'data' in result_data:
                        data = result_data['data']
                        if not data or data == {}:
                            print("❌ ISSUE: Data field is empty!")
                        else:
                            print(f"✅ Data has {len(data)} fields")
                            print(f"📝 Query: {data.get('query', 'N/A')}")
                            print(f"🤖 AI Overview: {'Found' if data.get('ai_overview_found') else 'Not found'}")
                    else:
                        print("❌ ISSUE: No 'data' field in response!")
                    
                    break
                elif result_data.get('status') == 'pending':
                    continue
                else:
                    print(f"❌ Unexpected status: {result_data}")
                    break
            else:
                print(f"❌ Error polling: {result_response.status_code}")
                break
        else:
            print("⏰ Timeout - job didn't complete")
    else:
        print(f"❌ Error submitting job: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    test_api_response()
