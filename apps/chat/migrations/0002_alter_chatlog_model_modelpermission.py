# pylint: disable=R0801,C0103

import django.db.models.deletion
import ovinc_client.core.models
import ovinc_client.core.utils
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("chat", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="chatlog",
            name="model",
            field=models.CharField(
                blank=True,
                choices=[
                    ("gpt-3.5-turbo", "GPT3.5 Turbo"),
                    ("gpt-3.5-turbo-0613", "GPT3.5 Turbo (0613)"),
                    ("gpt-3.5-turbo-16k", "GPT3.5 Turbo (16K)"),
                    ("gpt-3.5-turbo-16k-0613", "GPT3.5 Turbo (16K, 0613)"),
                    ("gpt-4", "GPT4"),
                    ("gpt-4-0613", "GPT4 (0613)"),
                    ("gpt-4-32k", "GPT4 (32K)"),
                    ("gpt-4-32k-0613", "GPT4 (32K, 0613)"),
                ],
                db_index=True,
                max_length=64,
                null=True,
                verbose_name="Model",
            ),
        ),
        migrations.CreateModel(
            name="ModelPermission",
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
                    "model",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("gpt-3.5-turbo", "GPT3.5 Turbo"),
                            ("gpt-3.5-turbo-0613", "GPT3.5 Turbo (0613)"),
                            ("gpt-3.5-turbo-16k", "GPT3.5 Turbo (16K)"),
                            ("gpt-3.5-turbo-16k-0613", "GPT3.5 Turbo (16K, 0613)"),
                            ("gpt-4", "GPT4"),
                            ("gpt-4-0613", "GPT4 (0613)"),
                            ("gpt-4-32k", "GPT4 (32K)"),
                            ("gpt-4-32k-0613", "GPT4 (32K, 0613)"),
                        ],
                        db_index=True,
                        max_length=64,
                        null=True,
                        verbose_name="Model",
                    ),
                ),
                ("expired_at", models.DateTimeField(blank=True, null=True, verbose_name="Expire Time")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Create Time")),
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
                "verbose_name": "Model Permission",
                "verbose_name_plural": "Model Permission",
                "ordering": ["-created_at"],
                "index_together": {("user", "model", "expired_at")},
            },
        ),
    ]
