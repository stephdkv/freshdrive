from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('rentals', '0014_rentalapplication_discount'),
    ]
    operations = [
        migrations.AddField(
            model_name='rentalapplication',
            name='how_did_you_find_us',
            field=models.CharField(
                max_length=32,
                choices=[
                    ("friends", "От друзей / знакомых"),
                    ("internet", "Из интернета / через поиск (Google, Яндекс)"),
                    ("ads", "Увидел рекламу"),
                    ("repeat_customer", "У вас брал услугу раньше / уже был клиентом"),
                    ("catalog", "Нашли вас в каталоге / на картах (Google Maps, 2ГИС, Яндекс.Справочник)")
                ],
                null=True,
                blank=True,
                verbose_name="Откуда о нас узнали",
                help_text="Как клиент узнал о нас"
            ),
        ),
    ] 