"""
Fix Docker Desktop issues
"""
import subprocess
import time

def fix_docker():
    print("🔧 Fixing Docker Desktop...")
    
    # Stop Docker Desktop
    print("\n1️⃣ Stopping Docker Desktop...")
    try:
        subprocess.run(['taskkill', '/F', '/IM', 'Docker Desktop.exe'], check=False)
        time.sleep(5)
        print("✅ Docker Desktop stopped")
    except:
        print("⚠ Could not stop Docker Desktop")
    
    # Clean up Docker resources
    print("\n2️⃣ Cleaning Docker resources...")
    try:
        # Remove all containers
        subprocess.run(['docker', 'rm', '-f', '$(docker ps -aq)'], shell=True, check=False)
        # Remove all images
        subprocess.run(['docker', 'rmi', '-f', '$(docker images -q)'], shell=True, check=False)
        print("✅ Docker resources cleaned")
    except:
        print("⚠ Could not clean Docker resources")
    
    # Restart Docker Desktop
    print("\n3️⃣ Restarting Docker Desktop...")
    try:
        # Start Docker Desktop
        subprocess.Popen(['C:\\Program Files\\Docker\\Docker\\Docker Desktop.exe'])
        print("✅ Docker Desktop starting...")
        
        # Wait for Docker to be ready
        print("\n⏳ Waiting for Docker to be ready...")
        for i in range(30):  # Wait up to 30 seconds
            try:
                result = subprocess.run(['docker', 'info'], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    print(f"\n✅ Docker is ready after {i+1} seconds!")
                    return True
            except:
                pass
            time.sleep(1)
        
        print("\n❌ Docker failed to start properly")
        return False
        
    except Exception as e:
        print(f"❌ Failed to restart Docker: {e}")
        return False

if __name__ == "__main__":
    if fix_docker():
        print("\n🚀 Docker is ready! You can now run:")
        print("   docker compose up -d")
    else:
        print("\n❌ Docker fix failed. Please:")
        print("   1. Restart Docker Desktop manually")
        print("   2. Check Docker Desktop logs")
        print("   3. Reinstall Docker Desktop if needed")
