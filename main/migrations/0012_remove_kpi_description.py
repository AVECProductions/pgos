# Generated by Django 5.1.5 on 2025-02-04 14:48

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0011_alter_journalentry_options_remove_journalentry_title'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='kpi',
            name='description',
        ),
    ]
