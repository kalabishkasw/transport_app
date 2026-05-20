# міграція:
# - індекс на Order.contact_email (filter __iexact у portal.views)
# - MaxValueValidator(100) для PromoCode.discount_percent
# - нове поле Order.loyalty_redeemed_amount (бали окремо від discount промокоду)

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0005_order_loyalty_awarded_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='loyalty_redeemed_amount',
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text='Сума, оплачена бонусними балами (1 бал = 1 EUR).',
                max_digits=10,
                verbose_name='Використано балами',
            ),
        ),
        migrations.AlterField(
            model_name='order',
            name='contact_email',
            field=models.EmailField(blank=True, db_index=True, max_length=254, verbose_name='Email'),
        ),
        migrations.AlterField(
            model_name='order',
            name='discount_amount',
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text='Сума знижки від промокоду у валюті замовлення.',
                max_digits=10,
                verbose_name='Сума знижки',
            ),
        ),
        migrations.AlterField(
            model_name='promocode',
            name='discount_percent',
            field=models.PositiveSmallIntegerField(
                help_text='Відсоток знижки від суми замовлення (1-100)',
                validators=[
                    django.core.validators.MinValueValidator(1),
                    django.core.validators.MaxValueValidator(100),
                ],
                verbose_name='Знижка, %',
            ),
        ),
    ]
