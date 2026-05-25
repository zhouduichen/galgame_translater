"""Quick integration test for the parsing pipeline."""
import json
import os
import time

import httpx

BASE = "http://127.0.0.1:8000/api/projects"
client = httpx.Client(timeout=30, follow_redirects=True)

# 1. Create project
resp = client.post(BASE, json={"title": "Pipeline Final Test"})
resp.raise_for_status()
pid = resp.json()["id"]
print(f"Project: {pid}")

# 2. Submit parse
novel = "Akira walked through the empty school hallway at sunset. She stopped at the music room, hearing Haruki play piano. When he noticed her, he smiled. Did you need something? She shook her head. Just wanted to hear you play. It sounds like goodbye. Haruki paused. Maybe it is. For now."
resp = client.post(f"{BASE}/{pid}/parse", json={"novel_text": novel, "target_length": "10min_demo"})
resp.raise_for_status()
job = resp.json()
print(f"Job: {job['job_id']} status={job['status']}")

# 3. Poll for completion
print("Waiting for worker to process...")
for i in range(90):
    time.sleep(2)
    resp = client.get(f"{BASE}/{pid}/jobs")
    jobs = resp.json()
    for j in jobs:
        if j["status"] in ("completed", "failed"):
            print(f"Job {j['job_id']}: {j['status']}")
            if j["status"] == "failed":
                print(f"  Error: {j.get('error', '')[:500]}")
            elif j["status"] == "completed":
                result = j.get("result", {})
                print(f"  Result keys: {list(result.keys())}")
                print(f"  Draft chars: {result.get('characters_count', 'N/A')}")
                print(f"  Draft scenes: {result.get('scenes_count', 'N/A')}")
            exit(0)
    if i % 10 == 0:
        print(f"  Still waiting... ({i*2}s)")

print("Timeout waiting for worker")
