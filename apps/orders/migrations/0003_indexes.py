# Migration for adding database indexes on frequently filtered fields.
# Created manually to support performance optimization for dashboard and reports.
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0002_promocode_order_discount_amount_order_promo_code'),
        ('routes', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='trip',
            field=models.ForeignKey(
                db_index=True,
                on_delete=models.deletion.PROTECT,
                related_name='orders',
                to='routes.trip',
                verbose_name='Рейс',
            ),
        ),
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending', 'Очікує підтвердження'),
                    ('confirmed', 'Підтверджене'),
                    ('paid', 'Оплачене'),
                    ('in_progress', 'Поїздка триває'),
                    ('completed', 'Завершене'),
                    ('cancelled', 'Скасоване'),
                    ('refunded', 'Повернено кошти'),
                ],
                db_index=True,
                default='pending',
                max_length=15,
                verbose_name='Статус',
            ),
        ),
        migrations.AlterField(
            model_name='ticket',
            name='status',
            field=models.CharField(
                choices=[
                    ('booked', 'Заброньований'),
                    ('paid', 'Оплачений'),
                    ('used', 'Використаний'),
                    ('cancelled', 'Скасований'),
                    ('refunded', 'Повернутий'),
                ],
                db_index=True,
                default='booked',
                max_length=10,
                verbose_name='Статус',
            ),
        ),
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['-created_at'], name='orders_orde_created_idx'),
        ),
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['status', '-created_at'], name='orders_orde_status_idx'),
        ),
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['trip', 'status'], name='orders_orde_trip_st_idx'),
        ),
        migrations.AddIndex(
            model_name='ticket',
            index=models.Index(fields=['order', 'status'], name='orders_tick_order_st_idx'),
        ),
    ]
