# Generated by Django 5.1.5 on 2025-02-03 20:43

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0003_alter_userprofile_role_quarterlygoal_kpi_yearlygoal_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='quarterlygoal',
            name='yearly_goal',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='main.yearlygoal'),
        ),
    ]
