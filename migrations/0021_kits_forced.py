# Generated by Django 3.1.7 on 2021-07-09 13:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0020_alerts_itemexpiry'),
    ]

    operations = [
        migrations.AddField(
            model_name='kits',
            name='forced',
            field=models.BooleanField(default=False),
        ),
    ]
