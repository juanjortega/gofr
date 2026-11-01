"""Genera .env con credenciales aleatorias para el despliegue local de GOFR. No sobrescribe uno existente
ni imprime los valores. Uso: python scripts/generar_env.py"""
import os
import secrets

RUTA = os.path.join(os.path.dirname(__file__), '..', '.env')

if os.path.exists(RUTA):
    print('.env ya existe; no se modifica')
else:
    with open(RUTA, 'w', encoding='utf-8') as f:
        f.write('GOFR_DB_PASSWORD=%s\n' % secrets.token_urlsafe(24))
    print('.env generado')
