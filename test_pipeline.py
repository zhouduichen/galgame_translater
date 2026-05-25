"""Quick integration test for the parsing pipeline."""
import json
import os
import time
import sys

import httpx

BASE = "http://127.0.0.1:8001/api/projects"
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
                print(f"  Project ID: {result.get('project_id', 'N/A')}")
                print(f"  Characters: {result.get('characters_count', 'N/A')}")
                print(f"  Scenes: {result.get('scenes_count', 'N/A')}")
                # Verify project loads
                project_resp = client.get(f"{BASE}/{pid}")
                project = project_resp.json()
                print(f"\n  Promoted project: '{project.get('title')}'")
                print(f"  Start scene: {project.get('start_scene_id', 'N/A')}")
                char_count = len(project.get("characters", {}))
                scene_count = len(project.get("scenes", {}))
                print(f"  DB characters: {char_count}, scenes: {scene_count}")
            exit(0)
    if i % 10 == 0:
        print(f"  Still waiting... ({i*2}s)")

print("Timeout waiting for worker")
