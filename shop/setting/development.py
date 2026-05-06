from .base import *

# Debug específico para desarrollo
DEBUG = True

# Base de datos para desarrollo (PostgreSQL)
DATABASES = {
    'default': {
        'ENGINE': os.getenv('DB_ENGINE', 'django.db.backends.postgresql'),
        'NAME': os.getenv('DB_NAME', 'shop_db'),
        'USER': os.getenv('DB_USER', 'postgres'),
        'PASSWORD': os.getenv('DB_PASSWORD', '1234'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}

# CORS para desarrollo
CORS_ALLOWED_ORIGINS = [
    "http://localhost:4200",
    "http://localhost:4201",
]

# Mostrar SQL queries en consola (opcional)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django.db.backends': {
            'handlers': ['console'],
            #'level': 'DEBUG',  # Cambiar a INFO para menos detalle
            'level':'ERROR',
            'propagate': False,

        },
    },
}