# Generated by Django 3.2.9 on 2023-12-05 07:32

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('community', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='comment',
            old_name='created_time',
            new_name='create_time',
        ),
        migrations.RenameField(
            model_name='commentcomment',
            old_name='created_time',
            new_name='create_time',
        ),
        migrations.RenameField(
            model_name='post',
            old_name='created_time',
            new_name='create_time',
        ),
    ]