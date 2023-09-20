# pylint: disable=R0801,C0103

import django.db.models.deletion
import ovinc_client.core.models
import ovinc_client.core.utils
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ChatLog",
            fields=[
                (
                    "id",
                    ovinc_client.core.models.UniqIDField(
                        default=ovinc_client.core.utils.uniq_id_without_time,
                        max_length=32,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "chat_id",
                    models.CharField(blank=True, db_index=True, max_length=255, null=True, verbose_name="Chat ID"),
                ),
                (
                    "model",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("gpt-4", "GPT4"),
                            ("gpt-4-0613", "GPT4 (0613)"),
                            ("gpt-4-32k", "GPT4 (32K)"),
                            ("gpt-4-32k-0613", "GPT4 (32K, 0613)"),
                            ("gpt-3.5-turbo", "GPT3.5 Turbo"),
                            ("gpt-3.5-turbo-0613", "GPT3.5 Turbo (0613)"),
                            ("gpt-3.5-turbo-16k", "GPT3.5 Turbo (16K)"),
                            ("gpt-3.5-turbo-16k-0613", "GPT3.5 Turbo (16K, 0613)"),
                        ],
                        db_index=True,
                        max_length=64,
                        null=True,
                        verbose_name="Model",
                    ),
                ),
                ("messages", models.JSONField(blank=True, null=True, verbose_name="Prompt Content")),
                ("content", models.TextField(blank=True, null=True, verbose_name="Completion Content")),
                ("prompt_tokens", models.IntegerField(default=int, verbose_name="Prompt Tokens")),
                ("completion_tokens", models.IntegerField(default=int, verbose_name="Completion Tokens")),
                (
                    "prompt_token_unit_price",
                    models.DecimalField(
                        decimal_places=10, default=float, max_digits=20, verbose_name="Prompt Token Unit Price"
                    ),
                ),
                (
                    "completion_token_unit_price",
                    models.DecimalField(
                        decimal_places=10, default=float, max_digits=20, verbose_name="Completion Token Unit Price"
                    ),
                ),
                ("created_at", models.BigIntegerField(db_index=True, verbose_name="Create Time")),
                (
                    "finished_at",
                    models.BigIntegerField(blank=True, db_index=True, null=True, verbose_name="Finish Time"),
                ),
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
                "verbose_name": "Chat Log",
                "verbose_name_plural": "Chat Log",
                "ordering": ["-created_at"],
            },
        ),
    ]
