# Generated by Django 5.2.1 on 2025-05-27 08:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rentals', '0002_alter_rentalapplication_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='transport',
            name='price_30_plus_days',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='Цена от 30 суток (за сутки)'),
        ),
        migrations.AddField(
            model_name='transport',
            name='price_3_6_days',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='Цена за 3-6 суток (за сутки)'),
        ),
        migrations.AddField(
            model_name='transport',
            name='price_7_30_days',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='Цена за 7-30 суток (за сутки)'),
        ),
        migrations.AddField(
            model_name='transport',
            name='price_per_day',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='Цена за сутки'),
        ),
    ]
