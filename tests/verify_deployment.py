
import urllib.request
import urllib.error
import time
import subprocess
import sys
import os
import signal

def run_verification():
    print("Starting uvicorn...")
    # Start uvicorn in background
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "faim.api.app:app", "--port", "8001", "--host", "127.0.0.1"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for startup
    print("Waiting for startup...")
    time.sleep(5)
    
    base_url = "http://127.0.0.1:8001"
    success = True
    
    try:
        # 1. Health Check
        try:
            with urllib.request.urlopen(f"{base_url}/api/v1/health") as response:
                if response.status == 200:
                    print("✅ Health check passed")
                else:
                    print(f"❌ Health check failed: {response.status}")
                    success = False
        except Exception as e:
            print(f"❌ Health check exception: {e}")
            success = False

        # 2. Auth Check (Expect 401)
        try:
            req = urllib.request.Request(f"{base_url}/api/v1/projects")
            urllib.request.urlopen(req)
            print("❌ Auth check failed: Expected 401, got 200")
            success = False
        except urllib.error.HTTPError as e:
            if e.code == 401:
                print("✅ Auth enforcement passed (Got expected 401)")
            else:
                print(f"❌ Auth check failed: Expected 401, got {e.code}")
                success = False
        except Exception as e:
            print(f"❌ Auth check exception: {e}")
            success = False

    finally:
        print("Stopping uvicorn...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except:
            proc.kill()
            
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    run_verification()
