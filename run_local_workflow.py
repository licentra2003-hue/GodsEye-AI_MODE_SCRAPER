#!/usr/bin/env python3
"""
Local Workflow Setup Script
Triggers the main workflow without Docker using existing components
"""
import subprocess
import time
import requests
import json
import os
import signal
import sys

# Configuration
RABBITMQ_CONTAINER = "godseye-rabbitmq-local"
GATEWAY_PORT = "8080"
GATEWAY_URL = f"http://localhost:{GATEWAY_PORT}/api/v1/scrape"

class LocalWorkflow:
    def __init__(self):
        self.processes = []
        self.rabbitmq_running = False
        
    def start_rabbitmq(self):
        """Start RabbitMQ using Docker (only for RabbitMQ)"""
        print("1. Starting RabbitMQ...")
        try:
            # Check if container exists
            result = subprocess.run(
                ["docker", "ps", "-a", "--filter", f"name={RABBITMQ_CONTAINER}"],
                capture_output=True, text=True
            )
            
            if RABBITMQ_CONTAINER in result.stdout:
                # Container exists, check if running
                result = subprocess.run(
                    ["docker", "ps", "--filter", f"name={RABBITMQ_CONTAINER}"],
                    capture_output=True, text=True
                )
                
                if RABBITMQ_CONTAINER in result.stdout:
                    print("   RabbitMQ already running")
                    self.rabbitmq_running = True
                else:
                    # Start existing container
                    subprocess.run(["docker", "start", RABBITMQ_CONTAINER], check=True)
                    print("   RabbitMQ started")
                    self.rabbitmq_running = True
            else:
                # Create new container
                subprocess.run([
                    "docker", "run", "-d",
                    "--name", RABBITMQ_CONTAINER,
                    "-p", "5672:5672",
                    "-p", "15672:15672",
                    "-e", "RABBITMQ_DEFAULT_USER=admin",
                    "-e", "RABBITMQ_DEFAULT_PASS=admin123",
                    "rabbitmq:3.12-management-alpine"
                ], check=True)
                print("   RabbitMQ container created and started")
                self.rabbitmq_running = True
                
            # Wait for RabbitMQ to be ready
            print("   Waiting for RabbitMQ to be ready...")
            time.sleep(5)
            
        except subprocess.CalledProcessError as e:
            print(f"   ERROR: Failed to start RabbitMQ: {e}")
            return False
        
        return True
    
    def start_gateway(self):
        """Start the API Gateway locally"""
        print("2. Starting API Gateway...")
        try:
            # Set environment variables
            env = os.environ.copy()
            env["RABBITMQ_URL"] = "amqp://admin:admin123@localhost:5672/"
            env["PORT"] = GATEWAY_PORT
            
            print(f"   RABBITMQ_URL: {env['RABBITMQ_URL']}")
            print(f"   PORT: {env['PORT']}")
            
            # Start Go gateway using go run (binary is Linux-only)
            process = subprocess.Popen(
                ["go", "run", "main.go"],
                cwd="gateway",
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT  # Combine stdout and stderr
            )
            self.processes.append(("Gateway", process))
            
            # Wait for gateway to start
            print("   Waiting for Gateway to start...")
            time.sleep(3)
            
            # Check if gateway is running
            try:
                response = requests.get(f"http://localhost:{GATEWAY_PORT}/health", timeout=2)
                if response.status_code == 200:
                    print("   Gateway started successfully")
                    return True
            except:
                pass
            
            print("   ERROR: Gateway failed to start")
            return False
            
        except Exception as e:
            print(f"   ERROR: Failed to start Gateway: {e}")
            return False
    
    def start_worker(self):
        """Start the Worker locally"""
        print("3. Starting Worker...")
        try:
            # Set environment variables
            env = os.environ.copy()
            env["RABBITMQ_URL"] = "amqp://admin:admin123@localhost:5672/"
            env["HEADLESS"] = "false"  # Use GUI browser for local testing
            env["STORAGE_MODE_API"] = "true"
            env["CALLBACK_API_URL"] = f"http://localhost:{GATEWAY_PORT}/api/scrape-result"
            env["DEBUG"] = "true"
            
            # Start Python worker
            process = subprocess.Popen(
                ["python", "worker_main.py"],
                cwd="worker",
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            self.processes.append(("Worker", process))
            
            print("   Worker started")
            time.sleep(2)
            
            return True
            
        except Exception as e:
            print(f"   ERROR: Failed to start Worker: {e}")
            return False
    
    def submit_test_job(self):
        """Submit a test job to the workflow"""
        print("4. Submitting test job...")
        
        test_data = {
            "query": "what is artificial intelligence",
            "location": "USA"
        }
        
        try:
            response = requests.post(GATEWAY_URL, json=test_data, timeout=10)
            
            if response.status_code in [200, 202]:
                job_data = response.json()
                job_id = job_data.get('job_id')
                print(f"   Job submitted successfully!")
                print(f"   Job ID: {job_id}")
                return job_id
            else:
                print(f"   ERROR: Job submission failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"   ERROR: Failed to submit job: {e}")
            return None
    
    def poll_job_result(self, job_id):
        """Poll for job results"""
        print("5. Polling for results...")
        
        result_url = f"http://localhost:{GATEWAY_PORT}/api/job-result/{job_id}"
        
        for attempt in range(30):  # 30 attempts = 5 minutes
            try:
                response = requests.get(result_url, timeout=5)
                result_data = response.json()
                
                status = result_data.get('status')
                print(f"   Attempt {attempt + 1}/30: Status = {status}")
                
                if status == 'completed':
                    print(f"\n   Job completed successfully!")
                    print(f"   AI Mode Found: {result_data.get('ai_mode_found')}")
                    print(f"   AI Mode Text: {result_data.get('ai_mode_text')}")
                    print(f"   Sources Count: {len(result_data.get('source_links', []))}")
                    print(f"\n   Full Results:")
                    print(json.dumps(result_data, indent=6))
                    return True
                elif status == 'failed':
                    print(f"   Job failed: {result_data.get('error_message')}")
                    return False
                    
            except Exception as e:
                print(f"   Polling error: {e}")
            
            time.sleep(10)  # Wait 10 seconds between polls
        
        print("   Job timed out after 5 minutes")
        return False
    
    def cleanup(self):
        """Clean up all processes"""
        print("\n6. Cleaning up...")
        
        # Stop all processes
        for name, process in self.processes:
            try:
                process.terminate()
                process.wait(timeout=5)
                print(f"   {name} stopped")
            except:
                try:
                    process.kill()
                    print(f"   {name} killed")
                except:
                    pass
        
        # Stop RabbitMQ container
        if self.rabbitmq_running:
            try:
                subprocess.run(["docker", "stop", RABBITMQ_CONTAINER], check=True)
                subprocess.run(["docker", "rm", RABBITMQ_CONTAINER], check=True)
                print("   RabbitMQ stopped and removed")
            except:
                pass
    
    def run(self):
        """Run the complete workflow"""
        print("=" * 60)
        print("LOCAL WORKFLOW TEST")
        print("Using existing components without modification")
        print("=" * 60)
        print()
        
        try:
            # Start components
            if not self.start_rabbitmq():
                print("ERROR: Failed to start RabbitMQ")
                return False
            
            if not self.start_gateway():
                print("ERROR: Failed to start Gateway")
                self.cleanup()
                return False
            
            if not self.start_worker():
                print("ERROR: Failed to start Worker")
                self.cleanup()
                return False
            
            print("\n" + "=" * 60)
            print("WORKFLOW READY")
            print("=" * 60)
            print()
            print("Components running:")
            print("  - RabbitMQ: localhost:5672")
            print("  - Gateway: localhost:8080")
            print("  - Worker: Running")
            print()
            print("You can observe the browser window (HEADLESS=false)")
            print()
            
            # Submit test job
            job_id = self.submit_test_job()
            if not job_id:
                print("ERROR: Failed to submit job")
                self.cleanup()
                return False
            
            # Poll for results
            print("\n" + "=" * 60)
            print("JOB PROCESSING")
            print("=" * 60)
            print()
            
            success = self.poll_job_result(job_id)
            
            print("\n" + "=" * 60)
            print("TEST RESULTS")
            print("=" * 60)
            
            if success:
                print("SUCCESS: Workflow completed successfully")
                print("The existing workflow works with HEADLESS=false")
            else:
                print("FAILED: Workflow did not complete")
            
            # Keep running for observation
            print("\nPress Enter to cleanup and exit...")
            input()
            
            return success
            
        except KeyboardInterrupt:
            print("\n\nInterrupted by user")
            return False
        finally:
            self.cleanup()

if __name__ == "__main__":
    workflow = LocalWorkflow()
    success = workflow.run()
    
    print("\n" + "=" * 60)
    print("FINAL RESULT")
    print("=" * 60)
    
    if success:
        print("SUCCESS: Local workflow test completed")
        print("The main workflow works without Docker")
    else:
        print("FAILED: Local workflow test failed")
    
    sys.exit(0 if success else 1)
