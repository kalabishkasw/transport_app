# індекс на Customer.is_active бо dashboard робить count(is_active=True)
# по таблиці. без індексу seq scan на кожен запит дашборда.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('customers', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customer',
            name='is_active',
            field=models.BooleanField(db_index=True, default=True, verbose_name='Активний'),
        ),
    ]
