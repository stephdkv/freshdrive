from django.db import migrations, models

HOW_DID_YOU_FIND_US_CHOICES = [
    ("friends", "От друзей / знакомых"),
    ("internet", "Из интернета / через поиск (Google, Яндекс)"),
    ("ads", "Увидел рекламу"),
    ("repeat_customer", "У вас брал услугу раньше / уже был клиентом"),
    ("catalog", "Нашли вас в каталоге / на картах (Google Maps, 2ГИС, Яндекс.Справочник)"),
    ("other", "Другое"),
]

class Migration(migrations.Migration):
    dependencies = [
        ('rentals', '0016_client_how_did_you_find_us'),
    ]
    operations = [
        migrations.AlterField(
            model_name='client',
            name='how_did_you_find_us',
            field=models.CharField(
                max_length=32,
                choices=HOW_DID_YOU_FIND_US_CHOICES,
                null=True,
                blank=True,
                verbose_name="Откуда о нас узнали",
                help_text="Как клиент узнал о нас"
            ),
        ),
        migrations.AlterField(
            model_name='rentalapplication',
            name='how_did_you_find_us',
            field=models.CharField(
                max_length=32,
                choices=HOW_DID_YOU_FIND_US_CHOICES,
                null=True,
                blank=True,
                verbose_name="Откуда о нас узнали",
                help_text="Как клиент узнал о нас"
            ),
        ),
    ] 