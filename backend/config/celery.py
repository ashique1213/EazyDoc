import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

app = Celery("eazydoc")

# Read config from Django settings, the CELERY namespace means all celery-related
# configuration keys should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover task modules from all registered Django apps.
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Simple ping/health task for verifying Celery worker connectivity."""
    print(f"Request: {self.request!r}")
    return "pong"
