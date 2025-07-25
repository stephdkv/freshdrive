# Generated by Django 5.2.1 on 2025-06-26 06:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rentals', '0021_merge_20250625_1342'),
    ]

    operations = [
        migrations.AddField(
            model_name='rentalapplication',
            name='original_total_cost',
            field=models.DecimalField(blank=True, decimal_places=0, help_text='Сумма аренды до досрочного возврата (для внутреннего пользования)', max_digits=10, null=True, verbose_name='Исходная сумма аренды'),
        ),
    ]
