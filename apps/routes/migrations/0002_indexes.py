# Migration for adding indexes to Trip model.
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('routes', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='trip',
            name='departure_at',
            field=models.DateTimeField(db_index=True, verbose_name='Час відправлення'),
        ),
        migrations.AlterField(
            model_name='trip',
            name='status',
            field=models.CharField(
                choices=[
                    ('planned', 'Запланований'),
                    ('on_sale', 'У продажу'),
                    ('in_progress', 'У дорозі'),
                    ('completed', 'Завершений'),
                    ('cancelled', 'Скасований'),
                ],
                db_index=True,
                default='planned',
                max_length=15,
                verbose_name='Статус',
            ),
        ),
        migrations.AddIndex(
            model_name='trip',
            index=models.Index(fields=['status', 'departure_at'], name='routes_trip_status_dep_idx'),
        ),
        migrations.AddIndex(
            model_name='trip',
            index=models.Index(fields=['route', 'departure_at'], name='routes_trip_route_dep_idx'),
        ),
    ]
