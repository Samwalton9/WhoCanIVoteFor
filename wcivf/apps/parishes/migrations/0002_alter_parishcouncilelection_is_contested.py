# Generated by Django 3.2 on 2021-09-28 13:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("parishes", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="parishcouncilelection",
            name="is_contested",
            field=models.BooleanField(null=True),
        ),
    ]
