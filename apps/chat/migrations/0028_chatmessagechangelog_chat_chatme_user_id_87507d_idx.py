# pylint: disable=R0801,C0103
# Generated by Django 4.2.17 on 2025-01-03 06:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chat", "0027_chatmessagechangelog"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="chatmessagechangelog",
            index=models.Index(fields=["user", "message_id", "created_at"], name="chat_chatme_user_id_87507d_idx"),
        ),
    ]
