# Generated by Django 5.1.5 on 2025-02-03 20:45

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0004_alter_quarterlygoal_yearly_goal'),
    ]

    operations = [
        migrations.RenameField(
            model_name='quarterlygoal',
            old_name='title',
            new_name='life_sector',
        ),
    ]
