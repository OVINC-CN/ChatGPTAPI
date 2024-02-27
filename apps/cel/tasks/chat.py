from django.db import transaction
from django.db.models import F, Func, Value
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
    logs = ChatLog.objects.filter(is_charged=False)

    # charge
    for log in logs:
        usage = log.prompt_tokens + log.completion_tokens
        with transaction.atomic():
            ChatLog.objects.filter(id=log.id).update(is_charged=True)
            ModelPermission.objects.filter(user=log.user, model=log.model).update(
                available_usage=Func(
                    F("available_usage") - usage,
                    Value(0),
                    function="GREATEST",
                )
            )
