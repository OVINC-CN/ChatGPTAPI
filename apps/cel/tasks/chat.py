from django.db import transaction
from django.db.models import F, Func, Value
from django.shortcuts import get_object_or_404
from ovinc_client.core.lock import task_lock

from apps.cel import app
from apps.chat.models import ChatLog, ModelPermission


@app.task(bind=True)
@task_lock()
def check_usage_limit(self):
    """
    Check Model Usage Limit
    """

    # load logs
    logs = ChatLog.objects.filter(is_charged=False, finished_at__isnull=False).values_list("id", flat=True)

    # charge
    for log_id in logs:
        calculate_usage_limit.apply_async(kwargs={"log_id": log_id})


@app.task(bind=True)
@transaction.atomic()
def calculate_usage_limit(self, log_id: str):
    """
    Calculate Model Usage Limit
    """

    log = get_object_or_404(ChatLog, id=log_id)

    usage = log.prompt_tokens + log.completion_tokens
    ChatLog.objects.filter(id=log.id).update(is_charged=True)
    ModelPermission.objects.filter(user=log.user, model=log.model).update(
        available_usage=Func(
            F("available_usage") - usage,
            Value(0),
            function="GREATEST",
        )
    )
