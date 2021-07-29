# Generated by Django 3.1.7 on 2021-05-30 04:20

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0012_kit_transactions'),
    ]

    operations = [
        migrations.AlterField(
            model_name='kit_transactions',
            name='kitloancart',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='transaction', to='inventory.kitloancart'),
        ),
        migrations.AlterField(
            model_name='kit_transactions',
            name='restock_order',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='kit_transaction', to='inventory.order'),
        ),
    ]
