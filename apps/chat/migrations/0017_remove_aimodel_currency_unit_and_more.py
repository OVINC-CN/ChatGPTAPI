# pylint: disable=R0801,C0103
# Generated by Django 4.2.13 on 2024-07-02 07:25

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("chat", "0016_aimodel_support_system_define"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="aimodel",
            name="currency_unit",
        ),
        migrations.RemoveField(
            model_name="chatlog",
            name="currency_unit",
        ),
    ]