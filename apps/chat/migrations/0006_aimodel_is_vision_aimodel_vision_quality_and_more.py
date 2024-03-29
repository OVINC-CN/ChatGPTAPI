# pylint: disable=C0103
# Generated by Django 4.2.3 on 2024-02-27 03:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chat", "0005_aimodel"),
    ]

    operations = [
        migrations.AddField(
            model_name="aimodel",
            name="is_vision",
            field=models.BooleanField(default=False, verbose_name="Is Vision"),
        ),
        migrations.AddField(
            model_name="aimodel",
            name="vision_quality",
            field=models.CharField(
                blank=True,
                choices=[("standard", "Standard"), ("hd", "HD")],
                max_length=64,
                null=True,
                verbose_name="Vision Quality",
            ),
        ),
        migrations.AddField(
            model_name="aimodel",
            name="vision_size",
            field=models.CharField(
                blank=True,
                choices=[("256x256", "256x256"), ("512x512", "512x512"), ("1024x1024", "1024x1024")],
                max_length=64,
                null=True,
                verbose_name="Vision Size",
            ),
        ),
        migrations.AddField(
            model_name="aimodel",
            name="vision_style",
            field=models.CharField(
                blank=True,
                choices=[("vivid", "Vivid"), ("nature", "Nature")],
                max_length=64,
                null=True,
                verbose_name="Vision Style",
            ),
        ),
    ]
