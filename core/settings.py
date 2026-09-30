"""
Django settings para el Sistema de Recomendación de Laptops.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# ─── Rutas base ───────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

# Cargar variables de entorno desde .env
load_dotenv(BASE_DIR / '.env')

# ─── Seguridad ────────────────────────────────────────────────────────────────
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-clave-de-desarrollo-local')
DEBUG = os.environ.get('DEBUG', 'True') == 'True'
_raw_hosts = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1,.onrender.com')
ALLOWED_HOSTS = [h.strip() for h in _raw_hosts.split(',') if h.strip()]
if 'testserver' not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append('testserver')


# ─── Aplicaciones instaladas ──────────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Terceros
    'rest_framework',
    'corsheaders',
    # Apps propias
    'equipos',
    'recomendaciones',
]

# ─── Middleware ───────────────────────────────────────────────────────────────
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',   # Debe ir primero
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Sirve archivos estáticos en producción
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

from urllib.parse import urlparse, unquote

# ── Base de datos ──────────────────────────────────────────────────
# Prioridad:
# 1. DATABASE_URL (URL de conexión completa de Render o PostgreSQL)
# 2. Variables individuales: DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT
# 3. SQLite solo si USE_SQLITE=True explícito
_database_url = os.environ.get('DATABASE_URL', '').strip()
_use_sqlite = os.environ.get('USE_SQLITE', 'False').lower() in ('true', '1')

if not _use_sqlite and _database_url:
    _parsed = urlparse(_database_url)
    _db_host = _parsed.hostname or 'localhost'
    if _db_host.startswith('dpg-') and '.' not in _db_host:
        _db_host = f"{_db_host}.oregon-postgres.render.com"
    _db_config = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': unquote(_parsed.path.lstrip('/')),
        'USER': unquote(_parsed.username or ''),
        'PASSWORD': unquote(_parsed.password or ''),
        'HOST': _db_host,
        'PORT': str(_parsed.port or 5432),
    }
    # Render y conexiones remotas de PostgreSQL requieren SSL
    if 'render.com' in _db_host or os.environ.get('DB_SSL', 'true').lower() == 'true':
        _db_config['OPTIONS'] = {'sslmode': 'require'}

    DATABASES = {'default': _db_config}

elif not _use_sqlite:
    _db_host = os.environ.get('DB_HOST', 'localhost')
    _db_config = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME':     os.environ.get('DB_NAME', 'laptops_db'),
        'USER':     os.environ.get('DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST':     _db_host,
        'PORT':     os.environ.get('DB_PORT', '5432'),
    }
    if 'render.com' in _db_host or os.environ.get('DB_SSL', 'false').lower() == 'true':
        _db_config['OPTIONS'] = {'sslmode': 'require'}

    DATABASES = {'default': _db_config}

else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# ─── Validación de contraseñas ────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ─── Internacionalización ─────────────────────────────────────────────────────
LANGUAGE_CODE = 'es-co'
TIME_ZONE = 'America/Bogota'
USE_I18N = True
USE_TZ = True

# ─── Archivos estáticos ───────────────────────────────────────────────────────
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ─── Django REST Framework ────────────────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# ─── CORS ─────────────────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = [
    'http://localhost:5173',   # Vite dev server
    'http://localhost:3000',
]
CORS_ALLOW_CREDENTIALS = True
