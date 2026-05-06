

import os

from django.core.wsgi import get_wsgi_application

env = os.getenv('DJANGO_ENV', 'development').lower()
settings_module = 'shop.setting.production' if env == 'production' else 'shop.setting.development'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', settings_module)

application = get_wsgi_application()
