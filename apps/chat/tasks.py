import datetime

from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404
from django.utils import timezone
from httpx import Client
from ovinc_client.core.lock import task_lock
from ovinc_client.core.logger import celery_logger

from apps.cel import app
from apps.chat.models import AIModel, ChatLog, ChatMessageChangeLog, OpenRouterModelInfo
from apps.wallet.models import Wallet


@app.task(bind=True)
@transaction.atomic()
def calculate_usage_limit(self, log_id: str):
    """
    Calculate Model Usage Limit
    """

    log = get_object_or_404(ChatLog, id=log_id)
    usage = log.prompt_tokens + log.completion_tokens
    celery_logger.info(
        "[CalculateUsageLimit] LogID: %s; User: %s; Model: %s; Usage: %d; Vision: %d",
        log_id,
        log.user.username,
        log.model,
        usage,
        log.vision_count,
    )

    ChatLog.objects.filter(id=log.id).update(is_charged=True)
    Wallet.objects.filter(user=log.user).update(
        balance=F("balance")
        - (log.prompt_tokens * log.prompt_token_unit_price / 1000)
        - (log.completion_tokens * log.completion_token_unit_price / 1000)
        - (log.vision_count * log.vision_unit_price / 1000)
        - (log.request_unit_price / 1000)
    )


@app.task(bind=True)
@task_lock()
def openrouter_model_sync(self):
    """
    Sync Model From OpenRouter
    """

    celery_logger.info("[SyncOpenRouterPrice] Start %s", self.request.id)

    if not settings.ENABLE_OPENROUTER_PRICE_SYNC:
        celery_logger.info("[SyncOpenRouterPrice] Not Enabled %s", self.request.id)
        return

    with Client(
        http2=True,
        headers={"Authorization": f"Bearer {settings.OPENROUTER_API_KEY}"},
        timeout=settings.OPENROUTER_API_TIMEOUT,
    ) as client:
        data = client.get(f"{settings.OPENROUTER_API_BASE.rstrip("/")}/models").json().get("data", [])

    openrouter_model_map = {m["id"]: OpenRouterModelInfo(**m) for m in data}

    db_models = AIModel.objects.all()
    for db_model in db_models:
        model_settings = db_model.settings or {}
        openrouter_model_id = model_settings.get("openrouter_model_id")
        if not openrouter_model_id:
            continue
        openrouter_model = openrouter_model_map.get(openrouter_model_id)
        if not openrouter_model:
            celery_logger.error("[SyncOpenRouterPrice] Model ID Invalid: %s", db_model.model)
            continue
        db_model.prompt_price = openrouter_model.pricing.prompt * 1000 * settings.OPENROUTER_EXCHANGE_RATE
        db_model.completion_price = openrouter_model.pricing.completion * 1000 * settings.OPENROUTER_EXCHANGE_RATE
        db_model.vision_price = openrouter_model.pricing.image * 1000 * settings.OPENROUTER_EXCHANGE_RATE
        db_model.request_price = openrouter_model.pricing.request * 1000 * settings.OPENROUTER_EXCHANGE_RATE
        db_model.save(update_fields=["prompt_price", "completion_price", "vision_price", "request_price"])
        celery_logger.info(
            "[SyncOpenRouterPrice] Model Price Updated: %s %s %s %s %s",
            db_model.model,
            db_model.prompt_price,
            db_model.completion_price,
            db_model.vision_price,
            db_model.request_price,
        )

    celery_logger.info("[SyncOpenRouterPrice] End %s", self.request.id)


@app.task(bind=True)
@task_lock()
def delete_old_history(self):
    """
    Delete Old Message History
    """

    celery_logger.info("[DeleteOldMessageHistory] Start %s", self.request.id)

    logs = ChatMessageChangeLog.objects.filter(
        created_at__lt=(timezone.now() - datetime.timedelta(days=settings.MESSAGE_LOG_RETAIN_DAYS))
    ).prefetch_related("user")
    celery_logger.info("[DeleteOldMessageHistory] Total: %d", logs.count())
    for log in logs:
        celery_logger.info(
            "[DeleteOldMessageHistory] ID: %d; User: %s; MessageID: %s; CreatedAt: %s",
            log.id,
            log.user,
            log.message_id,
            log.created_at,
        )
    logs.delete()

    celery_logger.info("[DeleteOldMessageHistory] End %s", self.request.id)
