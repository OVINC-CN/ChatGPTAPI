# pylint: disable=R0801,C0103

import ovinc_client.core.models
import ovinc_client.core.utils
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chat", "0004_alter_chatlog_model_alter_modelpermission_model_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="AIModel",
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
                    "provider",
                    models.CharField(
                        choices=[
                            ("openai", "Open AI"),
                            ("google", "Google"),
                            ("baidu", "Baidu"),
                            ("tencent", "Tencent"),
                        ],
                        db_index=True,
                        max_length=64,
                        verbose_name="Provider",
                    ),
                ),
                ("model", models.CharField(db_index=True, max_length=64, verbose_name="Model")),
                ("name", models.CharField(max_length=64, verbose_name="Model Name")),
                ("is_enabled", models.BooleanField(db_index=True, default=True, verbose_name="Enabled")),
                ("prompt_price", models.DecimalField(decimal_places=10, max_digits=20, verbose_name="Prompt Price")),
                (
                    "completion_price",
                    models.DecimalField(decimal_places=10, max_digits=20, verbose_name="Completion Price"),
                ),
            ],
            options={
                "verbose_name": "AI Model",
                "verbose_name_plural": "AI Model",
                "ordering": ["provider", "name"],
                "unique_together": {("provider", "model")},
            },
        ),
    ]
