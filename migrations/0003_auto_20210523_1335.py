# Generated by Django 3.1.7 on 2021-05-23 05:35

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0002_auto_20210523_1329'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='cart',
            name='item',
        ),
        migrations.RemoveField(
            model_name='item',
            name='expirydates',
        ),
        migrations.RemoveField(
            model_name='kititems',
            name='item',
        ),
        migrations.RemoveField(
            model_name='loancart',
            name='item',
        ),
        migrations.RemoveField(
            model_name='loanoutstanding',
            name='item',
        ),
        migrations.RemoveField(
            model_name='tempcart',
            name='item',
        ),
        migrations.DeleteModel(
            name='ItemExpiry',
        ),
    ]
