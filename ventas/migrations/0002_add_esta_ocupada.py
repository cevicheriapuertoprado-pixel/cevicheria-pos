from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('ventas', '0001_initial'),  # reemplaza con tu última migración real
    ]

    operations = [
        migrations.AddField(
            model_name='mesa',
            name='esta_ocupada',
            field=models.BooleanField(default=False),
        ),
    ]
