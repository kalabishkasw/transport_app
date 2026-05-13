# Migration for adding indexes to Vehicle and Driver active flags.
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fleet', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='vehicle',
            name='is_active',
            field=models.BooleanField(db_index=True, default=True, verbose_name='В експлуатації'),
        ),
        migrations.AlterField(
            model_name='driver',
            name='is_available',
            field=models.BooleanField(db_index=True, default=True, verbose_name='Доступний для рейсів'),
        ),
    ]
