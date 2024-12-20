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
    "openrouter_model_sync": {
        "task": "apps.chat.tasks.openrouter_model_sync",
        "schedule": crontab(minute="*/10"),
        "args": (),
    }
}
