# init_render.py
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cevicheria.settings')
django.setup()

from django.core.management import call_command

# Aplica migraciones
call_command('migrate', interactive=False)

# Carga la carta desde backup_platos.json (solo si existe)
if os.path.exists('backup_platos.json'):
    call_command('loaddata', 'backup_platos.json')
