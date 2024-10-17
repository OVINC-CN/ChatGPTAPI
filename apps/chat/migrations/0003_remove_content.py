# pylint: disable=R0801,C0103

from django.conf import settings
from django.core.exceptions import FieldDoesNotExist
from django.db import migrations

from apps.chat.models import ChatLog


def remove_content(*args, **kwargs) -> None:
    if settings.RECORD_CHAT_CONTENT:
        return
    try:
        ChatLog.objects.all().update(messages=[], content="")
    except FieldDoesNotExist:
        pass


class Migration(migrations.Migration):
    dependencies = [
        ("chat", "0002_alter_chatlog_model_modelpermission"),
    ]

    operations = [
        migrations.RunPython(remove_content),
    ]
