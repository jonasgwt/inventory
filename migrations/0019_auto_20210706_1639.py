# Generated by Django 3.1.7 on 2021-07-06 08:39

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0018_alerts'),
    ]

    operations = [
        migrations.RenameField(
            model_name='alerts',
            old_name='expire',
            new_name='urgent',
        ),
    ]
