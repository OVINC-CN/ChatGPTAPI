from ovinc_client.core.lock import task_lock
from ovinc_client.core.logger import celery_logger

from apps.cel import app


@app.task(bind=True)
@task_lock()
def celery_debug(self):
    celery_logger.info(f"[CeleryDebug] Start {self.request.id}")
    celery_logger.info(f"[CeleryDebug] End {self.request.id}")
