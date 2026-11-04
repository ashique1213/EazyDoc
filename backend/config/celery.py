import logging
import os
import time
from celery import Celery
from celery.signals import task_prerun, task_postrun, task_failure, task_retry

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

app = Celery("eazydoc")

# Read config from Django settings with CELERY_ namespace prefix
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover task modules from all registered Django apps.
app.autodiscover_tasks()

logger = logging.getLogger("celery")


@task_prerun.connect
def on_task_prerun(sender=None, task_id=None, task=None, args=None, kwargs=None, **kw):
    """
    Executed immediately before a Celery task starts.
    Extracts correlation ID, sets execution context, and logs task start.
    """
    from config.logging import set_current_request_id

    # Extract correlation ID from task headers or kwargs
    correlation_id = None
    if task and hasattr(task, "request") and task.request:
        headers = getattr(task.request, "headers", None) or {}
        correlation_id = (
            headers.get("correlation_id")
            or headers.get("request_id")
            or getattr(task.request, "correlation_id", None)
        )
    if not correlation_id and kwargs and isinstance(kwargs, dict):
        correlation_id = kwargs.get("correlation_id") or kwargs.get("request_id")

    if correlation_id:
        set_current_request_id(str(correlation_id))

    if task:
        task._start_time = time.monotonic()

    logger.info(
        f"Celery task started: {sender.name if sender else 'unknown'}",
        extra={
            "task_id": task_id,
            "task_name": sender.name if sender else "unknown",
            "correlation_id": correlation_id or "-",
        },
    )


@task_postrun.connect
def on_task_postrun(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **kw):
    """
    Executed immediately after a Celery task completes.
    Computes runtime duration, logs completion status, and clears context.
    """
    from config.logging import clear_current_request_id

    duration_ms = 0.0
    if task and hasattr(task, "_start_time"):
        duration_ms = round((time.monotonic() - task._start_time) * 1000, 2)

    logger.info(
        f"Celery task finished: {sender.name if sender else 'unknown'} [{state}] in {duration_ms}ms",
        extra={
            "task_id": task_id,
            "task_name": sender.name if sender else "unknown",
            "state": state,
            "duration_ms": duration_ms,
        },
    )
    clear_current_request_id()


@task_failure.connect
def on_task_failure(sender=None, task_id=None, exception=None, args=None, kwargs=None, traceback=None, einfo=None, **kw):
    """
    Executed when a Celery task raises an unhandled exception or exhausts retries.
    """
    from config.logging import clear_current_request_id

    logger.error(
        f"Celery task failed permanently: {sender.name if sender else 'unknown'}: {exception}",
        extra={
            "task_id": task_id,
            "task_name": sender.name if sender else "unknown",
            "exception_type": exception.__class__.__name__ if exception else "Exception",
            "exception_message": str(exception) if exception else "",
        },
    )
    clear_current_request_id()


@task_retry.connect
def on_task_retry(sender=None, request=None, reason=None, einfo=None, **kw):
    """
    Executed when a Celery task schedules a retry.
    """
    task_id = getattr(request, "id", "-") if request else "-"
    task_name = sender.name if sender else "unknown"
    logger.warning(
        f"Celery task retrying: {task_name} [attempt {getattr(request, 'retries', 0) if request else 0}]: {reason}",
        extra={
            "task_id": task_id,
            "task_name": task_name,
            "retry_attempt": getattr(request, "retries", 0) if request else 0,
            "reason": str(reason),
        },
    )


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Simple ping/health task for verifying Celery worker connectivity."""
    print(f"Request: {self.request!r}")
    return "pong"
