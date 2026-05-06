from .base import *
import os

# Debug desactivado en producción
DEBUG = False

# Base de datos para producción
DATABASES = {
    'default': {
        'ENGINE': os.getenv('DB_ENGINE', 'django.db.backends.postgresql'),
        'NAME': os.getenv('DB_NAME_PROD', 'shop_db_prod'),
        'USER': os.getenv('DB_USER_PROD', 'postgres'),
        'PASSWORD': os.getenv('DB_PASSWORD_PROD', '1234'),
        'HOST': os.getenv('DB_HOST_PROD', ''),
        'PORT': os.getenv('DB_PORT_PROD', '5432'),
    }
}
# ============================================
# CORRECCIÓN: ALLOWED_HOSTS para Render
# ============================================
# Leer desde .env o usar valores por defecto
allowed_hosts_env = os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1')
ALLOWED_HOSTS = [host.strip() for host in allowed_hosts_env.split(',')]

# Agregar automáticamente el dominio de Render
# Esto es importante porque Render genera URLs dinámicas
ALLOWED_HOSTS.extend([
    '.onrender.com',  # Permite cualquier subdominio de onrender.com
    'localhost',
    '127.0.0.1',
])

allowed_hosts_env = os.getenv('DJANGO_ALLOWED_HOSTS', '')
ALLOWED_HOSTS = [host.strip() for host in allowed_hosts_env.split(',') if host]

ALLOWED_HOSTS.append('.onrender.com')

# CORS para producción
cors_origins = os.getenv('CORS_ALLOWED_ORIGINS_PROD', 'https://tudominio.com')
CORS_ALLOWED_ORIGINS = [origin.strip() for origin in cors_origins.split(',')]
# Agregar URL de Render automáticamente
CORS_ALLOWED_ORIGINS.append('https://*.onrender.com')

# Security settings para producción
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

print(f"🚀 Modo PRODUCCIÓN activado")
print(f"📋 ALLOWED_HOSTS: {ALLOWED_HOSTS}")
print(f"🔗 CORS_ALLOWED_ORIGINS: {CORS_ALLOWED_ORIGINS}")