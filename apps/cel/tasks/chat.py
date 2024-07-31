from asgiref.sync import async_to_sync
from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404
from ovinc_client.core.lock import task_lock
from ovinc_client.core.logger import celery_logger

from apps.cel import app
from apps.chat.consumers_async import AsyncConsumer
from apps.chat.models import ChatLog
from apps.wallet.models import Wallet


@app.task(bind=True)
@task_lock()
def check_usage_limit(self):
    """
    Check Model Usage Limit
    """

    celery_logger.info("[CheckUsageLimit] Start %s", self.request.id)

    # load logs
    logs = ChatLog.objects.filter(is_charged=False, finished_at__isnull=False).values_list("id", flat=True)
    celery_logger.info("[CheckUsageLimit] LogsCount: %d", len(logs))

    # charge
    for log_id in logs:
        calculate_usage_limit.apply_async(kwargs={"log_id": log_id})

    celery_logger.info("[CheckUsageLimit] End %s", self.request.id)


@app.task(bind=True)
@transaction.atomic()
def calculate_usage_limit(self, log_id: str):
    """
    Calculate Model Usage Limit
    """

    celery_logger.info("[CalculateUsageLimit] Start %s", self.request.id)

    log = get_object_or_404(ChatLog, id=log_id)
    usage = log.prompt_tokens + log.completion_tokens
    celery_logger.info(
        "[CalculateUsageLimit] LogID: %s; User: %s; Model: %s; Usage: %d",
        log_id,
        log.user.username,
        log.model,
        usage,
    )

    ChatLog.objects.filter(id=log.id).update(is_charged=True)
    Wallet.objects.filter(user=log.user).update(
        balance=F("balance")
        - (log.prompt_tokens * log.prompt_token_unit_price / 1000)
        - (log.completion_tokens * log.completion_token_unit_price / 1000)
    )

    celery_logger.info("[CalculateUsageLimit] End %s", self.request.id)


@app.task(bind=True)
def async_reply(self, channel_name: str, key: str):
    """
    Async Reply to User
    """

    async_to_sync(AsyncConsumer(channel_name=channel_name, key=key).chat)()
