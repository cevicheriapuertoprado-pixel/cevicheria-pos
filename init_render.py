# init_render.py (o un script aparte)
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cevicheria.settings')
django.setup()

from ventas.models import Mesa
from django.contrib.auth.models import User

# Crear 18 mesas si no existen
for i in range(1, 19):
    Mesa.objects.get_or_create(numero=i)

# Crear superusuario admin si no existe
if not User.objects.filter(username='CEVICHERIA').exists():
    User.objects.create_superuser('CEVICHERIA', 'cevicheriapuertoprado', 'puertoprado2025')
