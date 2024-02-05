# pylint: disable=R0801,C0103

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chat", "0003_remove_content"),
    ]

    operations = [
        migrations.AlterField(
            model_name="chatlog",
            name="model",
            field=models.CharField(blank=True, db_index=True, max_length=64, null=True, verbose_name="Model"),
        ),
        migrations.AlterField(
            model_name="modelpermission",
            name="model",
            field=models.CharField(blank=True, db_index=True, max_length=64, null=True, verbose_name="Model"),
        ),
    ]
