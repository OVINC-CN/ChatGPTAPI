# pylint: disable=R0801,C0103
# Generated by Django 4.2.16 on 2024-12-11 11:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chat", "0019_alter_chatlog_index_together"),
    ]

    operations = [
        migrations.AddField(
            model_name="aimodel",
            name="support_vision",
            field=models.BooleanField(default=False, verbose_name="Support Vision"),
        ),
        migrations.AlterField(
            model_name="aimodel",
            name="provider",
            field=models.CharField(
                choices=[
                    ("openai", "Open AI"),
                    ("google", "Google"),
                    ("tencent", "Tencent"),
                    ("midjourney", "Midjourney"),
                    ("moonshot", "Moonshot"),
                ],
                db_index=True,
                max_length=64,
                verbose_name="Provider",
            ),
        ),
    ]