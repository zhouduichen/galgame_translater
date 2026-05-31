"""Background worker: polls generation_jobs table and processes tasks."""

from __future__ import annotations

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from project_model.schema_version import check_schema_version

load_dotenv()

from .tasks import TASK_HANDLERS

POLL_INTERVAL = 5  # seconds — only used when idle
MAX_WORKERS = int(os.environ.get("WORKER_MAX_THREADS", "3"))
DATA_DIR = Path(os.environ.get("GALGAME_DB_DIR", str(Path(__file__).resolve().parent.parent.parent.parent / "api" / "data")))
BATCH_SIZE = 10

# Existing databases must be migrated explicitly before the worker starts.
check_schema_version(DATA_DIR / "galgame.db")


def _claim_pending_jobs(limit: int = BATCH_SIZE) -> list[dict]:
    db_path = DATA_DIR / "galgame.db"
    if not db_path.exists():
        return []

    import sqlite3

    conn = sqlite3.connect(str(db_path), timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("BEGIN IMMEDIATE")
        rows = [
            dict(r)
            for r in conn.execute(
                """SELECT id, project_id, job_type, payload, result
                   FROM generation_jobs
                   WHERE status = 'pending'
                   ORDER BY created_at ASC
                   LIMIT ?""",
                (limit,),
            ).fetchall()
        ]
        now = datetime.now(timezone.utc).isoformat()
        for row in rows:
            conn.execute(
                "UPDATE generation_jobs SET status = 'running', progress = 0.0, updated_at = ? WHERE id = ? AND status = 'pending'",
                (now, row["id"]),
            )
        conn.commit()
        return rows
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _update_job(job_id: str, **kwargs):
    db_path = DATA_DIR / "galgame.db"
    import sqlite3

    conn = sqlite3.connect(str(db_path))
    sets = ", ".join(f"{k} = ?" for k in kwargs)
    conn.execute(
        f"UPDATE generation_jobs SET {sets}, updated_at = ? WHERE id = ?",
        [*kwargs.values(), datetime.now(timezone.utc).isoformat(), job_id],
    )
    conn.commit()
    conn.close()


def _job_result_failed(result: object) -> bool:
    return isinstance(result, dict) and result.get("status") == "error"


def _process_one(job: dict) -> None:
    """Process a single job. Updates DB on completion/failure.

    Checks for cancellation before writing final status to avoid
    overwriting a manual cancel that arrived between job claim and
    handler completion.
    """
    handler = TASK_HANDLERS.get(job["job_type"])
    if handler is None:
        print(f"[worker] Unknown job type: {job['job_type']}")
        _update_job(job["id"], status="failed", error=f"Unknown job type: {job['job_type']}")
        return

    print(f"[worker] Processing {job['id']} ({job['job_type']})")

    def _is_cancelled() -> bool:
        db_path = DATA_DIR / "galgame.db"
        if not db_path.exists():
            return False
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        try:
            row = conn.execute("SELECT status FROM generation_jobs WHERE id = ?", (job["id"],)).fetchone()
            return row is not None and row[0] == "cancelled"
        finally:
            conn.close()

    try:
        payload = json.loads(job["payload"]) if isinstance(job["payload"], str) else job["payload"]
        payload["job_id"] = job["id"]
        result = handler(payload)

        # Final cancellation check before writing result
        if _is_cancelled():
            print(f"[worker] {job['id']} was cancelled — skipping final write")
            return

        if _job_result_failed(result):
            _update_job(
                job["id"],
                status="failed",
                progress=1.0,
                result=json.dumps(result, ensure_ascii=False),
                error=str(result.get("error", "Task returned error status")),
            )
            print(f"[worker] Failed {job['id']}: {result.get('error', 'Task returned error status')}")
        else:
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


def main():
    print(f"[worker] Starting. Max workers: {MAX_WORKERS}. Poll interval (idle): {POLL_INTERVAL}s.")
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        while True:
            try:
                jobs = _claim_pending_jobs()
                if jobs:
                    futures = {executor.submit(_process_one, job): job["id"] for job in jobs}
                    for future in as_completed(futures):
                        try:
                            future.result()
                        except Exception as e:
                            print(f"[worker] Unhandled error in job {futures[future]}: {e}")
                    # Immediately check for more work — no sleep when work was found
                    continue
                time.sleep(POLL_INTERVAL)
            except KeyboardInterrupt:
                print("\n[worker] Shutting down. Waiting for in-flight jobs...")
                executor.shutdown(wait=True, cancel_futures=False)
                break
            except Exception as e:
                print(f"[worker] Error: {e}")
                time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
