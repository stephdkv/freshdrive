# Generated by Django 5.2.1 on 2025-05-28 03:30

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rentals', '0010_rentalapplication_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='rentalapplication',
            name='transport',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='rental_applications', to='rentals.transport', verbose_name='Транспорт'),
        ),
    ]
