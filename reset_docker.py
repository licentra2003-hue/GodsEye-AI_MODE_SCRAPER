"""
Complete Docker reset and restart
"""
import subprocess
import time
import os

def reset_docker():
    print("🔄 Complete Docker Reset")
    print("="*50)
    
    # Kill all Docker processes
    print("\n1️⃣ Killing all Docker processes...")
    try:
        subprocess.run(['taskkill', '/F', '/IM', 'Docker Desktop.exe'], check=False)
        subprocess.run(['taskkill', '/F', '/IM', 'com.docker.backend.exe'], check=False)
        time.sleep(3)
        print("✅ Docker processes killed")
    except:
        print("⚠ Could not kill Docker processes")
    
    # Clean up Docker files
    print("\n2️⃣ Cleaning Docker files...")
    docker_paths = [
        os.path.expanduser(r'~\AppData\Local\Docker'),
        os.path.expanduser(r'~\AppData\Roaming\Docker'),
        r'C:\ProgramData\Docker',
        r'C:\Program Files\Docker'
    ]
    
    for path in docker_paths:
        if os.path.exists(path):
            try:
                # Just remove temp files, not the whole installation
                temp_path = os.path.join(path, 'tmp')
                if os.path.exists(temp_path):
                    import shutil
                    shutil.rmtree(temp_path)
                    print(f"✅ Cleaned {temp_path}")
            except:
                pass
    
    # Restart Docker Desktop
    print("\n3️⃣ Restarting Docker Desktop...")
    try:
        # Start Docker Desktop
        docker_exe = r'C:\Program Files\Docker\Docker\Docker Desktop.exe'
        if os.path.exists(docker_exe):
            subprocess.Popen([docker_exe])
            print("✅ Docker Desktop starting...")
            
            # Wait for Docker to be ready
            print("\n⏳ Waiting for Docker to initialize (this might take 2-3 minutes)...")
            
            for i in range(180):  # Wait up to 3 minutes
                try:
                    # Check if Docker is responding
                    result = subprocess.run(['docker', 'version'], capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        print(f"\n✅ Docker is ready after {i+1} seconds!")
                        return True
                except:
                    pass
                
                # Show progress
                if i % 30 == 0 and i > 0:
                    print(f"   Still waiting... ({i//60} minute{'' if i//60 == 1 else 's'} passed)")
                
                time.sleep(1)
            
            print("\n❌ Docker failed to initialize")
            return False
        else:
            print("❌ Docker Desktop not found at expected location")
            return False
            
    except Exception as e:
        print(f"❌ Failed to restart Docker: {e}")
        return False

def test_docker():
    """Test if Docker is working"""
    print("\n🧪 Testing Docker...")
    
    # Test basic Docker command
    try:
        result = subprocess.run(['docker', 'run', '--rm', 'hello-world'], capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print("✅ Docker is working!")
            return True
        else:
            print(f"❌ Docker test failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Docker test error: {e}")
        return False

if __name__ == "__main__":
    print("⚠ This will completely reset Docker Desktop")
    print("   Make sure you have saved any important containers/images")
    
    choice = input("\nContinue? (y/N): ")
    if choice.lower() == 'y':
        if reset_docker():
            if test_docker():
                print("\n🚀 Docker is ready! You can now run:")
                print("   docker compose up -d")
            else:
                print("\n❌ Docker is running but tests failed")
        else:
            print("\n❌ Docker reset failed")
            print("\n💡 Suggestions:")
            print("   1. Restart your computer")
            print("   2. Reinstall Docker Desktop")
            print("   3. Check Windows Subsystem for Linux (WSL2)")
    else:
        print("❌ Cancelled")
