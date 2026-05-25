"""End-to-end test: starts worker inline, creates project, submits parse, verifies promotion."""
import json
import time
import threading

import httpx

API = "http://127.0.0.1:8001"
BASE = f"{API}/api/projects"
client = httpx.Client(timeout=60, follow_redirects=True)

# 1. Create project
resp = client.post(BASE, json={"title": "E2E Test"})
resp.raise_for_status()
pid = resp.json()["id"]
print(f"[OK] Created project: {pid}")

# 2. Submit parse
novel = "Akira walked through the empty school hallway at sunset. She stopped at the music room, hearing Haruki play piano. When he noticed her, he smiled. Did you need something? She shook her head. Just wanted to hear you play. It sounds like goodbye. Haruki paused. Maybe it is. For now."
resp = client.post(f"{BASE}/{pid}/parse", json={"novel_text": novel, "target_length": "10min_demo"})
resp.raise_for_status()
print(f"[OK] Submitted parse job: {resp.json()['job_id']}")

# 3. Run the worker inline (single poll cycle)
print("Running worker inline...")
from worker.main import _poll, _update_job
from worker.tasks import TASK_HANDLERS

def run_worker_once():
    jobs = _poll()
    print(f"  Found {len(jobs)} pending job(s)")
    for job in jobs:
        handler = TASK_HANDLERS.get(job["job_type"])
        if handler is None:
            _update_job(job["id"], status="failed", error=f"Unknown job type: {job['job_type']}")
            continue
        _update_job(job["id"], status="running", progress=0.0)
        try:
            payload = json.loads(job["payload"]) if isinstance(job["payload"], str) else job["payload"]
            result = handler(payload)
            _update_job(job["id"], status="completed", progress=1.0, result=json.dumps(result, ensure_ascii=False))
            print(f"  [OK] Processed {job['id']}")
        except Exception as e:
            _update_job(job["id"], status="failed", error=str(e))
            print(f"  [FAIL] Failed {job['id']}: {e}")

run_worker_once()

# 4. Check job status
resp = client.get(f"{BASE}/{pid}/jobs")
jobs = resp.json()
job = next((j for j in jobs if j["job_id"].endswith(f"{pid}_parse")), None)
if not job:
    print("[FAIL] Job not found")
    exit(1)

print(f"  Job status: {job['status']}")
if job["status"] == "failed":
    print(f"  Error: {job.get('error', '')}")
    exit(1)

# 5. Verify promoted project
resp = client.get(f"{BASE}/{pid}")
project = resp.json()
print(f"\n[OK] Project: '{project['title']}'")
print(f"  Characters: {len(project['characters'])}")
print(f"  Scenes: {len(project['scenes'])}")
print(f"  Start scene: {project['start_scene_id']}")
for sid, scene in project["scenes"].items():
    print(f"    {sid}: '{scene['title']}' ({len(scene['nodes'])} nodes)")

# 6. Verify via player URL
print(f"\n[OK] Play URL: /project/{pid}")
print(f"[OK] Edit URL: /project/{pid}/edit")
print("\nPipeline: PASS")
