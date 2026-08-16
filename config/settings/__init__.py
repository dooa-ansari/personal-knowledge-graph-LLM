"""
Django settings package.

Routes to dev.py or prod.py based on the DJANGO_ENV environment variable.
Default: development
"""
import os

DJANGO_ENV = os.getenv('DJANGO_ENV', 'development').lower()

if DJANGO_ENV == 'production':
    from .prod import *  # noqa: F401, F403
else:
    from .dev import *  # noqa: F401, F403
