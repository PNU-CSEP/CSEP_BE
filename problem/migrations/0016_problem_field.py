# Generated by Django 3.2.9 on 2024-01-08 05:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('problem', '0015_auto_20231203_0742'),
    ]

    operations = [
        migrations.AddField(
            model_name='problem',
            name='field',
            field=models.BigIntegerField(default=0),
        ),
    ]
