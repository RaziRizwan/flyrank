"""
services/notify.py -- the confirmation "email" (console log, or force a failure for
testing PROBE 5). Runs as a FastAPI BackgroundTask, which means it executes only AFTER
the HTTP response has already been sent -- there is no code path where this function
raising can turn into a failed submission response. Retries with a short backoff; if it
never succeeds, the job is marked failed and an alert line is logged. That failure is
still invisible to the client, on purpose.
"""
import time

import repository


def send_confirmation(job_id: int, widget_id: int, submission_id: int, data: dict,
                       max_attempts: int = 3, force_failure: bool = False) -> None:
    for attempt in range(1, max_attempts + 1):
        try:
            _send(widget_id, submission_id, data, force_failure=force_failure)
            repository.mark_job_succeeded(job_id)
            return
        except Exception as e:
            if attempt == max_attempts:
                repository.mark_job_failed(job_id, str(e), attempt)
                print(f"[ALERT] notification job {job_id} failed after {attempt} attempts: {e}")
            else:
                time.sleep(0.2 * attempt)  # a small real backoff, not exponential -- this is a
                                            # capstone-scoped job queue, not a production one


def _send(widget_id: int, submission_id: int, data: dict, force_failure: bool = False) -> None:
    """Stands in for a real email/webhook call. force_failure exists purely so PROBE 5
    ("force the side effect to throw") is reproducible on demand rather than needing a
    genuinely broken SMTP server to test against."""
    if force_failure:
        raise RuntimeError("simulated notification failure (for testing)")
    print(f"[EMAIL] New submission #{submission_id} on widget {widget_id}: {data}")
