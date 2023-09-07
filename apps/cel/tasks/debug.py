from apps.cel import app
from apps.cel.utils import task_lock
from core.logger import celery_logger


@app.task(bind=True)
@task_lock()
def celery_debug(self):
    celery_logger.info(f"[CeleryDebug] Start {self.request.id}")
    celery_logger.info(f"[CeleryDebug] End {self.request.id}")
