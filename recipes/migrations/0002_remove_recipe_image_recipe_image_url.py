# Generated by Django 5.0.1 on 2025-02-16 19:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('recipes', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='recipe',
            name='image',
        ),
        migrations.AddField(
            model_name='recipe',
            name='image_url',
            field=models.URLField(blank=True),
        ),
    ]
