from worker.main import _job_result_failed


def test_job_result_failed_for_error_status() -> None:
    assert _job_result_failed({"status": "error", "error": "Empty novel text"}) is True


def test_job_result_not_failed_for_ok_status() -> None:
    assert _job_result_failed({"status": "ok"}) is False
