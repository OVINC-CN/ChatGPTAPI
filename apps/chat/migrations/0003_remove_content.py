from django.conf import settings
from django.db import migrations

from apps.chat.models import ChatLog


def remove_content(*args, **kwargs) -> None:
    if settings.RECORD_CHAT_CONTENT:
        return
    ChatLog.objects.all().update(messages=[], content="")


class Migration(migrations.Migration):
    dependencies = [
        ("chat", "0002_alter_chatlog_model_modelpermission"),
    ]

    operations = [
        migrations.RunPython(remove_content),
    ]
