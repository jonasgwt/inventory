# Generated by Django 3.1.7 on 2021-07-09 13:28

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0021_kits_forced'),
    ]

    operations = [
        migrations.AddField(
            model_name='tempcart',
            name='timeadded',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
    ]
