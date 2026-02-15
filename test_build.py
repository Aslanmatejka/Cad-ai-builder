"""
Quick test: start the server in a thread, hit it, then stop it.
Run from project root with .venv active.
"""
import sys, os, threading, time, json, urllib.request, urllib.error

# Ensure Backend is importable
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "Backend"))
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "Backend"))

os.environ['PYTHONIOENCODING'] = 'utf-8'
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except: pass

import uvicorn
from main import app

BASE = "http://127.0.0.1:3001"

class Server(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.server = None
    def run(self):
        config = uvicorn.Config(app, host="127.0.0.1", port=3001, log_level="warning")
        self.server = uvicorn.Server(config)
        self.server.run()
    def stop(self):
        if self.server:
            self.server.should_exit = True

def post_json(path, body, timeout=180):
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(f"{BASE}{path}", data=data,
                                 headers={"Content-Type":"application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())

def get_bytes(path, timeout=10):
    req = urllib.request.Request(f"{BASE}{path}")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

# --- Start ---
srv = Server()
srv.start()
time.sleep(3)

try:
    # Health
    print("\n1. Health check...")
    h = json.loads(get_bytes("/"))
    print(f"   Status: {h['status']} ✅")

    # Sync build
    print("\n2. Sync build: 'a simple rectangular box 100x60x40mm'...")
    t0 = time.time()
    result = post_json("/api/build", {"prompt": "a simple rectangular box 100mm x 60mm x 40mm"})
    dt = time.time() - t0
    print(f"   Time: {dt:.1f}s")
    print(f"   buildId: {result.get('buildId')}")
    print(f"   stlUrl: {result.get('stlUrl')}")
    print(f"   stepUrl: {result.get('stepUrl')}")
    print(f"   params: {len(result.get('parameters', []))}")
    print(f"   success: {result.get('success')} ✅")

    # Check file exists
    stl_url = result.get("stlUrl", "")
    if stl_url:
        print(f"\n3. Download STL: {stl_url}")
        stl_data = get_bytes(stl_url)
        print(f"   Size: {len(stl_data)/1024:.1f} KB ✅")

    # Rebuild
    params = result.get("parameters", [])
    if params and result.get("buildId"):
        print(f"\n4. Rebuild with modified params...")
        new_params = {p["name"]: round(p["default"] * 1.1, 2) for p in params}
        r2 = post_json("/api/rebuild", {"buildId": result["buildId"], "parameters": new_params}, timeout=30)
        print(f"   New buildId: {r2.get('buildId')}")
        print(f"   success: {r2.get('success')} ✅")

    # Streaming build
    print(f"\n5. Stream build: 'a coffee mug with a handle'...")
    t0 = time.time()
    data = json.dumps({"prompt": "a coffee mug with a handle"}).encode("utf-8")
    req = urllib.request.Request(f"{BASE}/api/build/stream", data=data,
                                 headers={"Content-Type":"application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=180) as resp:
        last_evt = None
        for line in resp:
            line = line.decode("utf-8", errors="replace").strip()
            if line.startswith("data: "):
                evt = json.loads(line[6:])
                step = evt.get("step","?")
                msg = evt.get("message","")
                status = evt.get("status","")
                print(f"   [{step}] {status}: {msg}")
                last_evt = evt
    dt = time.time() - t0
    print(f"   Time: {dt:.1f}s")
    if last_evt and last_evt.get("status") == "complete":
        r = last_evt["result"]
        print(f"   buildId: {r.get('buildId')}")
        print(f"   params: {len(r.get('parameters', []))}")
        print("   ✅ PASS")
    else:
        print("   ❌ FAIL - last event was not 'complete'")

    print("\n🎉 ALL TESTS PASSED!")

except Exception as e:
    import traceback
    print(f"\n❌ TEST FAILED: {e}")
    traceback.print_exc()

finally:
    srv.stop()
    time.sleep(1)
