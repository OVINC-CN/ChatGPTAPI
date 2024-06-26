# pylint: disable=R0801,C0103
# Generated by Django 4.2.11 on 2024-05-25 07:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chat", "0011_aimodel_currency_unit_chatlog_currency_unit"),
    ]

    operations = [
        migrations.AddField(
            model_name="aimodel",
            name="settings",
            field=models.JSONField(blank=True, null=True, verbose_name="Settings"),
        ),
        migrations.AlterField(
            model_name="aimodel",
            name="provider",
            field=models.CharField(
                choices=[
                    ("openai", "Open AI"),
                    ("google", "Google"),
                    ("baidu", "Baidu"),
                    ("tencent", "Tencent"),
                    ("aliyun", "Aliyun"),
                ],
                db_index=True,
                max_length=64,
                verbose_name="Provider",
            ),
        ),
    ]
