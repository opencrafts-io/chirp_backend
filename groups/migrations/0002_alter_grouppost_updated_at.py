# Generated by Django 5.2.3 on 2025-07-05 09:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('groups', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='grouppost',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
