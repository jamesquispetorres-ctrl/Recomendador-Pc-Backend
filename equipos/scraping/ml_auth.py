"""
Módulo de autenticación OAuth 2.0 para la API de Mercado Libre Perú (MPE).

Flujo implementado:
1. Generación de URL de autorización (Authorization Code Flow).
2. Canje de código de autorización por Access Token y Refresh Token.
3. Guardado automático de credenciales en el archivo .env.
4. Renovación automática (refresh_token) cuando el access_token expire.
"""
import logging
import os
import re
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse
import requests

logger = logging.getLogger(__name__)

AUTH_URL = 'https://auth.mercadolibre.com.pe/authorization'
TOKEN_URL = 'https://api.mercadolibre.com/oauth/token'

# Ruta al archivo .env del backend
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / '.env'


def get_ml_credentials():
    """
    Obtiene las credenciales de Mercado Libre desde variables de entorno.
    """
    client_id = os.environ.get('ML_CLIENT_ID', '').strip()
    client_secret = os.environ.get('ML_CLIENT_SECRET', '').strip()
    redirect_uri = os.environ.get('ML_REDIRECT_URI', 'https://localhost').strip()
    access_token = os.environ.get('ML_ACCESS_TOKEN', '').strip()
    refresh_token = os.environ.get('ML_REFRESH_TOKEN', '').strip()

    return {
        'client_id': client_id,
        'client_secret': client_secret,
        'redirect_uri': redirect_uri,
        'access_token': access_token,
        'refresh_token': refresh_token,
    }


def generar_url_autorizacion(client_id: str | None = None, redirect_uri: str | None = None) -> str:
    """
    Genera la URL de autorización para que el usuario abra en su navegador,
    inicie sesión en Mercado Libre y autorice la aplicación.

    Args:
        client_id: App ID de Mercado Libre.
        redirect_uri: URL de redirección configurada en la aplicación de Mercado Libre.

    Returns:
        URL de autorización completa.
    """
    creds = get_ml_credentials()
    c_id = client_id or creds['client_id']
    r_uri = redirect_uri or creds['redirect_uri']

    if not c_id:
        raise ValueError("ML_CLIENT_ID no configurado en variables de entorno o archivo .env")

    params = {
        'response_type': 'code',
        'client_id': c_id,
        'redirect_uri': r_uri,
    }

    return f"{AUTH_URL}?{urlencode(params)}"


def limpiar_codigo_autorizacion(codigo_o_url: str) -> str:
    """
    Extrae el código limpio si el usuario pega la URL completa de redirección
    (ej: https://localhost/?code=TG-66f8... o TG-66f8...).
    """
    texto = (codigo_o_url or '').strip()

    # Si es una URL completa
    if 'code=' in texto:
        parsed = urlparse(texto)
        qs = parse_qs(parsed.query)
        if 'code' in qs and qs['code']:
            return qs['code'][0].strip()

    # Si viene con comillas o espacios
    texto = texto.strip(' "\'()[]{}')
    return texto


def guardar_tokens_en_env(access_token: str, refresh_token: str) -> bool:
    """
    Actualiza o agrega automáticamente ML_ACCESS_TOKEN y ML_REFRESH_TOKEN
    en el archivo .env de forma segura y persistente.
    """
    try:
        # Actualizar en memoria del proceso actual
        os.environ['ML_ACCESS_TOKEN'] = access_token
        os.environ['ML_REFRESH_TOKEN'] = refresh_token

        if not ENV_PATH.exists():
            # Si no existe, crearlo
            with open(ENV_PATH, 'w', encoding='utf-8') as f:
                f.write(f"ML_ACCESS_TOKEN={access_token}\n")
                f.write(f"ML_REFRESH_TOKEN={refresh_token}\n")
            return True

        contenido = ENV_PATH.read_text(encoding='utf-8')

        # Reemplazar o agregar ML_ACCESS_TOKEN
        if re.search(r'^ML_ACCESS_TOKEN=.*$', contenido, flags=re.MULTILINE):
            contenido = re.sub(
                r'^ML_ACCESS_TOKEN=.*$',
                f"ML_ACCESS_TOKEN={access_token}",
                contenido,
                flags=re.MULTILINE,
            )
        else:
            contenido += f"\nML_ACCESS_TOKEN={access_token}"

        # Reemplazar o agregar ML_REFRESH_TOKEN
        if re.search(r'^ML_REFRESH_TOKEN=.*$', contenido, flags=re.MULTILINE):
            contenido = re.sub(
                r'^ML_REFRESH_TOKEN=.*$',
                f"ML_REFRESH_TOKEN={refresh_token}",
                contenido,
                flags=re.MULTILINE,
            )
        else:
            contenido += f"\nML_REFRESH_TOKEN={refresh_token}"

        ENV_PATH.write_text(contenido, encoding='utf-8')
        logger.info("[Mercado Libre OAuth] Tokens guardados exitosamente en %s", ENV_PATH)
        return True

    except Exception as exc:
        logger.error("[Mercado Libre OAuth] Error al guardar tokens en .env: %s", exc)
        return False


def canjear_codigo_por_token(
    codigo: str,
    client_id: str | None = None,
    client_secret: str | None = None,
    redirect_uri: str | None = None,
) -> dict:
    """
    Hace una petición POST al endpoint de token de Mercado Libre con el código
    de autorización recibido para obtener el access_token y refresh_token.
    """
    creds = get_ml_credentials()
    c_id = client_id or creds['client_id']
    c_secret = client_secret or creds['client_secret']
    r_uri = redirect_uri or creds['redirect_uri']

    codigo_limpio = limpiar_codigo_autorizacion(codigo)

    if not codigo_limpio:
        raise ValueError("El código de autorización no puede estar vacío.")

    if not c_id or not c_secret:
        raise ValueError("ML_CLIENT_ID y ML_CLIENT_SECRET son requeridos.")

    payload = {
        'grant_type': 'authorization_code',
        'client_id': c_id,
        'client_secret': c_secret,
        'code': codigo_limpio,
        'redirect_uri': r_uri,
    }

    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': 'LaptopAI-MercadoLibreClient/1.0',
    }

    logger.info("[Mercado Libre OAuth] Canjeando código de autorización por token...")

    response = requests.post(TOKEN_URL, data=payload, headers=headers, timeout=15)

    if response.status_code != 200:
        error_msg = f"Error al canjear código ({response.status_code}): {response.text}"
        logger.error("[Mercado Libre OAuth] %s", error_msg)
        raise RuntimeError(error_msg)

    data = response.json()
    new_access_token = data.get('access_token')
    new_refresh_token = data.get('refresh_token')

    if not new_access_token:
        raise RuntimeError(f"La respuesta no contiene access_token: {data}")

    # Guardar automáticamente en .env
    guardar_tokens_en_env(new_access_token, new_refresh_token)

    return data


def refrescar_token(
    client_id: str | None = None,
    client_secret: str | None = None,
    refresh_token: str | None = None,
) -> dict:
    """
    Usa el refresh_token para solicitar automáticamente un nuevo access_token
    y guarda los nuevos valores en el archivo .env.
    """
    creds = get_ml_credentials()
    c_id = client_id or creds['client_id']
    c_secret = client_secret or creds['client_secret']
    r_token = refresh_token or creds['refresh_token']

    if not r_token:
        raise ValueError("No hay refresh_token disponible para renovar la sesión.")

    if not c_id or not c_secret:
        raise ValueError("ML_CLIENT_ID y ML_CLIENT_SECRET son requeridos para renovar.")

    payload = {
        'grant_type': 'refresh_token',
        'client_id': c_id,
        'client_secret': c_secret,
        'refresh_token': r_token,
    }

    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': 'LaptopAI-MercadoLibreClient/1.0',
    }

    logger.info("[Mercado Libre OAuth] Renovando access_token usando refresh_token...")

    response = requests.post(TOKEN_URL, data=payload, headers=headers, timeout=15)

    if response.status_code != 200:
        error_msg = f"Error al refrescar token ({response.status_code}): {response.text}"
        logger.error("[Mercado Libre OAuth] %s", error_msg)
        raise RuntimeError(error_msg)

    data = response.json()
    new_access_token = data.get('access_token')
    new_refresh_token = data.get('refresh_token') or r_token

    if not new_access_token:
        raise RuntimeError(f"La respuesta de refresh no contiene access_token: {data}")

    # Guardar automáticamente la rotación de tokens en .env
    guardar_tokens_en_env(new_access_token, new_refresh_token)

    logger.info("[Mercado Libre OAuth] Token renovado exitosamente.")
    return data


def obtener_token_valido() -> str | None:
    """
    Devuelve el access_token actual. Si no hay access_token pero hay refresh_token,
    intenta renovarlo automáticamente.
    """
    creds = get_ml_credentials()
    token = creds['access_token']

    if token:
        return token

    # Si no hay token de acceso directo pero tenemos refresh_token, intentar refrescar
    if creds['refresh_token']:
        try:
            data = refrescar_token()
            return data.get('access_token')
        except Exception as exc:
            logger.warning("[Mercado Libre OAuth] No se pudo obtener token vía refresh: %s", exc)

    return None
