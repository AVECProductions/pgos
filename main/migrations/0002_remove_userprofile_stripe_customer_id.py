# Generated by Django 5.1.5 on 2025-01-28 21:34

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='userprofile',
            name='stripe_customer_id',
        ),
    ]
