import os

from celery import Celery
from celery.schedules import crontab
from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "entry.settings")
os.environ.setdefault("C_FORCE_ROOT", "True")

app = Celery("main", broker=settings.BROKER_URL)
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# Schedule Tasks
app.conf.beat_schedule = {
    "celery_debug": {
        "task": "apps.cel.tasks.debug.celery_debug",
        "schedule": crontab(minute="*"),
        "args": (),
    },
}
