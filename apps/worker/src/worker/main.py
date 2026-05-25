"""Background worker: polls generation_jobs table and processes tasks."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from .tasks import TASK_HANDLERS

POLL_INTERVAL = 5  # seconds
DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "api" / "data"


def _poll() -> list[dict]:
    """Read pending jobs from the SQLite DB directly."""
    db_path = DATA_DIR / "galgame.db"
    if not db_path.exists():
        return []

    import sqlite3

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(
        """SELECT id, project_id, job_type, payload, result
           FROM generation_jobs
           WHERE status = 'pending'
           ORDER BY created_at ASC
           LIMIT 5"""
    )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def _update_job(job_id: str, **kwargs):
    db_path = DATA_DIR / "galgame.db"
    import sqlite3

    conn = sqlite3.connect(str(db_path))
    sets = ", ".join(f"{k} = ?" for k in kwargs)
    conn.execute(
        f"UPDATE generation_jobs SET {sets}, updated_at = ? WHERE id = ?",
        [*kwargs.values(), datetime.utcnow().isoformat() + "Z", job_id],
    )
    conn.commit()
    conn.close()


def main():
    print(f"[worker] Starting. Polling every {POLL_INTERVAL}s...")
    while True:
        try:
            jobs = _poll()
            for job in jobs:
                handler = TASK_HANDLERS.get(job["job_type"])
                if handler is None:
                    print(f"[worker] Unknown job type: {job['job_type']}")
                    _update_job(job["id"], status="failed", error=f"Unknown job type: {job['job_type']}")
                    continue

                print(f"[worker] Processing {job['id']} ({job['job_type']})")
                _update_job(job["id"], status="running", progress=0.0)

                try:
                    payload = json.loads(job["payload"]) if isinstance(job["payload"], str) else job["payload"]
                    result = handler(payload)
                    _update_job(
                        job["id"],
                        status="completed",
                        progress=1.0,
                        result=json.dumps(result, ensure_ascii=False),
                    )
                    print(f"[worker] Completed {job['id']}")
                except Exception as e:
                    print(f"[worker] Failed {job['id']}: {e}")
                    _update_job(job["id"], status="failed", error=str(e))

            time.sleep(POLL_INTERVAL)
        except KeyboardInterrupt:
            print("\n[worker] Shutting down.")
            break
        except Exception as e:
            print(f"[worker] Error: {e}")
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
