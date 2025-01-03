# pylint: disable=R0801,C0103
# Generated by Django 4.2.17 on 2025-01-02 11:05

import django.db.models.deletion
import ovinc_client.core.models
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("chat", "0026_aimodel_icon"),
    ]

    operations = [
        migrations.CreateModel(
            name="ChatMessageChangeLog",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False, verbose_name="ID")),
                ("message_id", models.CharField(max_length=64, verbose_name="Message ID")),
                ("action", models.SmallIntegerField(choices=[(1, "Update"), (2, "Delete")], verbose_name="Action")),
                (
                    "content",
                    models.TextField(blank=True, help_text="Encrypted Message Content", verbose_name="Content"),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Create Time")),
                (
                    "user",
                    ovinc_client.core.models.ForeignKey(
                        db_constraint=False,
                        on_delete=django.db.models.deletion.PROTECT,
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="User",
                    ),
                ),
            ],
            options={
                "verbose_name": "Chat Message Change Log",
                "verbose_name_plural": "Chat Message Change Log",
                "ordering": ["-id"],
                "indexes": [models.Index(fields=["user", "created_at"], name="chat_chatme_user_id_21b322_idx")],
            },
        ),
    ]