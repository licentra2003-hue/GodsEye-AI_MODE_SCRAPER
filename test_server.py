#!/usr/bin/env python3
"""
Simple test server for local testing without RabbitMQ
"""
import asyncio
import json
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
from datetime import datetime
import uuid

app = FastAPI(title="GodsEye Test Server")

# In-memory storage for test results
job_results = {}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/api/v1/scrape")
async def submit_job(request: dict):
    """Submit a scrape job"""
    job_id = str(uuid.uuid4())
    
    # Store job as pending
    job_results[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "query": request.get("query"),
        "location": request.get("location"),
        "submitted_at": datetime.now().isoformat()
    }
    
    # Simulate processing delay
    asyncio.create_task(process_job_async(job_id, request))
    
    return {
        "job_id": job_id,
        "status": "queued",
        "message": "Job submitted for processing"
    }

@app.get("/api/job-result/{job_id}")
async def get_job_result(job_id: str):
    """Get job result"""
    if job_id not in job_results:
        return {
            "job_id": job_id,
            "message": "Job not found or still processing",
            "status": "pending"
        }
    
    return job_results[job_id]

async def process_job_async(job_id: str, request: dict):
    """Simulate job processing"""
    try:
        # Simulate processing time
        await asyncio.sleep(5)
        
        # Update job with results
        job_results[job_id].update({
            "status": "completed",
            "success": True,
            "ai_mode_found": True,
            "ai_mode_text": "This is simulated AI Mode content for testing purposes.",
            "source_links": [
                {
                    "url": "https://example.com/source1",
                    "text": "Example Source 1",
                    "snippet": "This is a test source link",
                    "position": 1,
                    "domain": "example.com",
                    "favicon_url": "",
                    "thumbnail_url": "",
                    "date": datetime.now().isoformat()
                }
            ],
            "completed_at": datetime.now().isoformat(),
            "query": request.get("query"),
            "location": request.get("location")
        })
        
        print(f"Job {job_id} completed successfully")
        
    except Exception as e:
        job_results[job_id].update({
            "status": "failed",
            "error_message": str(e),
            "completed_at": datetime.now().isoformat()
        })
        print(f"Job {job_id} failed: {e}")

if __name__ == "__main__":
    print("Starting GodsEye Test Server on http://localhost:8080")
    print("This is a mock server for testing without RabbitMQ")
    print("Available endpoints:")
    print("   - GET  /health")
    print("   - POST /api/v1/scrape")
    print("   - GET  /api/job-result/{job_id}")
    
    uvicorn.run(app, host="0.0.0.0", port=8080)
