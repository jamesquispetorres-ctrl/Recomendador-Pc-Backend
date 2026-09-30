"""
Cliente de SerpApi para Google Shopping (Perú)
Permite buscar laptops y PCs de escritorio reales a través de Google Shopping API.
"""
import os
import re
import logging
import requests
from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from equipos.models import Equipo, HistorialPrecio

logger = logging.getLogger(__name__)

BUSQUEDAS_PERU_DEFAULT = [
    "laptop precio Peru",
    "laptop gaming Peru",
    "PC escritorio Peru",
]


def limpiar_precio(precio_raw) -> Decimal:
    """
    Convierte cualquier formato de precio de SerpApi/Google Shopping a Decimal.
    Ejemplos: 'S/ 2,599.00', 'S/ 1.899,00', 2599, '2599.90', '$270.00'
    """
    if isinstance(precio_raw, (int, float)):
        return Decimal(str(precio_raw))
    if not precio_raw:
        return Decimal('0')

    texto = str(precio_raw)
    texto = re.sub(r'[^\d.,]', '', texto)
    if not texto:
        return Decimal('0')

    if '.' in texto and ',' in texto:
        if texto.rfind('.') > texto.rfind(','):
            texto = texto.replace(',', '')
        else:
            texto = texto.replace('.', '').replace(',', '.')
    elif ',' in texto:
        partes = texto.split(',')
        if len(partes[-1]) == 2:
            texto = texto.replace(',', '.')
        else:
            texto = texto.replace(',', '')
    elif '.' in texto:
        partes = texto.split('.')
        if len(partes) > 2 or (len(partes[-1]) == 3 and len(partes[0]) <= 3):
            texto = texto.replace('.', '')

    try:
        val = Decimal(texto)
        return val if val > Decimal('0') else Decimal('0')
    except Exception:
        return Decimal('0')


def inferir_especificaciones(titulo: str) -> dict:
    """
    Infiere especificaciones técnicas básicas a partir del título del producto.
    """
    titulo_lower = titulo.lower()

    marcas = [
        "Asus", "HP", "Lenovo", "Acer", "Dell", "MSI", "Apple", "Gigabyte",
        "Samsung", "LG", "Huawei", "TUF", "ROG", "Alienware", "Razer", "Advance"
    ]
    marca_encontrada = "Genérico"
    for m in marcas:
        if re.search(r'\b' + re.escape(m) + r'\b', titulo, re.IGNORECASE):
            marca_encontrada = m
            break

    procesador = "Intel Core i5 / AMD Ryzen 5"
    if "core i9" in titulo_lower or "i9" in titulo_lower:
        procesador = "Intel Core i9"
    elif "core i7" in titulo_lower or "i7" in titulo_lower:
        procesador = "Intel Core i7"
    elif "core i5" in titulo_lower or "i5" in titulo_lower:
        procesador = "Intel Core i5"
    elif "core i3" in titulo_lower or "i3" in titulo_lower:
        procesador = "Intel Core i3"
    elif "ryzen 9" in titulo_lower:
        procesador = "AMD Ryzen 9"
    elif "ryzen 7" in titulo_lower:
        procesador = "AMD Ryzen 7"
    elif "ryzen 5" in titulo_lower:
        procesador = "AMD Ryzen 5"
    elif "ryzen 3" in titulo_lower:
        procesador = "AMD Ryzen 3"
    elif "m1" in titulo_lower:
        procesador = "Apple M1"
    elif "m2" in titulo_lower:
        procesador = "Apple M2"
    elif "m3" in titulo_lower:
        procesador = "Apple M3"
    elif "celeron" in titulo_lower:
        procesador = "Intel Celeron"

    ram_match = re.search(r'(\d+)\s*(?:gb|gb ram|ram)', titulo_lower)
    ram = 16
    if ram_match:
        try:
            val = int(ram_match.group(1))
            if val in [4, 8, 12, 16, 24, 32, 64]:
                ram = val
        except ValueError:
            pass

    alm = "512GB SSD"
    if "1tb ssd" in titulo_lower or "1 tb ssd" in titulo_lower:
        alm = "1TB SSD"
    elif "2tb ssd" in titulo_lower or "2 tb ssd" in titulo_lower:
        alm = "2TB SSD"
    elif "256gb ssd" in titulo_lower or "256 gb ssd" in titulo_lower:
        alm = "256GB SSD"
    elif "512gb ssd" in titulo_lower or "512 gb ssd" in titulo_lower:
        alm = "512GB SSD"
    elif "1tb" in titulo_lower or "1 tb" in titulo_lower:
        alm = "1TB HDD/SSD"

    gpu = "Integrada"
    if "rtx 4090" in titulo_lower: gpu = "NVIDIA GeForce RTX 4090"
    elif "rtx 4080" in titulo_lower: gpu = "NVIDIA GeForce RTX 4080"
    elif "rtx 4070" in titulo_lower: gpu = "NVIDIA GeForce RTX 4070"
    elif "rtx 4060" in titulo_lower: gpu = "NVIDIA GeForce RTX 4060"
    elif "rtx 4050" in titulo_lower: gpu = "NVIDIA GeForce RTX 4050"
    elif "rtx 3060" in titulo_lower: gpu = "NVIDIA GeForce RTX 3060"
    elif "rtx 3050" in titulo_lower: gpu = "NVIDIA GeForce RTX 3050"
    elif "gtx" in titulo_lower: gpu = "NVIDIA GeForce GTX"
    elif "radeon" in titulo_lower: gpu = "AMD Radeon Graphics"

    pantalla_match = re.search(r'(\d{2}\.?\d?)\s*(?:"|pulgadas|pulg)', titulo_lower)
    pantalla = None
    if pantalla_match:
        try:
            val = float(pantalla_match.group(1))
            if 10.0 <= val <= 34.0:
                pantalla = val
        except ValueError:
            pass

    return {
        "marca": marca_encontrada,
        "procesador": procesador,
        "memoria_ram": ram,
        "almacenamiento": alm,
        "tarjeta_grafica": gpu,
        "tamanio_pantalla": pantalla,
    }


class SerpApiClient:
    """
    Cliente para la API de Google Shopping mediante SerpApi.
    """
    ENDPOINT = "https://serpapi.com/search"

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("SERPAPI_KEY")
        if not self.api_key:
            logger.warning("SERPAPI_KEY no está configurada en las variables de entorno.")

    def buscar_google_shopping(self, query: str) -> list:
        """
        Llama a la API de SerpApi para Google Shopping (gl=pe, hl=es, engine=google_shopping).
        Si la API retorna un error 400 por país gl no soportado en google_shopping,
        hace un fallback automático usando el término de búsqueda con filtro de país.
        """
        if not self.api_key:
            raise RuntimeError("SERPAPI_KEY faltante o no configurada en .env")

        params = {
            "engine": "google_shopping",
            "gl": "pe",
            "hl": "es",
            "q": query,
            "api_key": self.api_key,
        }

        try:
            response = requests.get(self.ENDPOINT, params=params, timeout=45)
            if response.status_code == 400 and ("gl" in response.text or "Unsupported" in response.text):
                # Fallback sin el parametro gl=pe incompatible
                params_fallback = {
                    "engine": "google_shopping",
                    "hl": "es",
                    "q": query,
                    "api_key": self.api_key,
                }
                response = requests.get(self.ENDPOINT, params=params_fallback, timeout=45)
        except requests.exceptions.RequestException as req_err:
            raise RuntimeError(f"Error de conexión con SerpApi: {req_err}")

        if response.status_code in (401, 429):
            raise RuntimeError(f"Respuesta SerpApi (HTTP {response.status_code}): Cuota agotada o API Key inválida.")

        response.raise_for_status()
        data = response.json()

        if "error" in data:
            raise RuntimeError(f"Error devuelto por SerpApi: {data['error']}")

        return data.get("shopping_results", [])

    @transaction.atomic
    def guardar_o_actualizar_producto(self, item: dict, termino_busqueda: str, dry_run: bool = False) -> tuple[str, bool]:
        """
        Extrae datos del producto devuelto por SerpApi y crea/actualiza el registro en Equipo.
        Registra la fecha de hoy en HistorialPrecio.

        Returns:
            (estado, es_nuevo) donde estado es 'creado', 'actualizado', o 'sin_cambio'
        """
        titulo = item.get("title") or item.get("name") or "Equipo Sin Nombre"
        price_raw = item.get("extracted_price") if "extracted_price" in item else item.get("price")
        precio_decimal = limpiar_precio(price_raw)

        if precio_decimal <= Decimal('0'):
            return ('sin_cambio', False)

        tienda = item.get("source") or item.get("merchant") or item.get("seller") or "Google Shopping"
        enlace = item.get("product_link") or item.get("link") or item.get("serpapi_product_api") or ""
        thumbnail = item.get("thumbnail") or item.get("image") or ""

        # Inferir tipo_equipo por palabra clave de búsqueda o título
        t_low = termino_busqueda.lower()
        tit_low = titulo.lower()
        if "pc" in t_low or "escritorio" in t_low or "desktop" in t_low or "escritorio" in tit_low or "pc gamer" in tit_low:
            tipo_equipo = "pc_escritorio"
        else:
            tipo_equipo = "laptop"

        specs = inferir_especificaciones(titulo)
        marca = specs["marca"]
        modelo = titulo[:200]

        equipo = None
        if enlace:
            equipo = Equipo.objects.filter(enlace_compra=enlace).first()
        if not equipo:
            equipo = Equipo.objects.filter(marca__iexact=marca, modelo__iexact=modelo, tienda=tienda).first()

        fecha_hoy = timezone.now().date()

        if equipo:
            precio_anterior = equipo.precio
            if precio_anterior != precio_decimal or thumbnail or enlace:
                if not dry_run:
                    if precio_anterior != precio_decimal:
                        HistorialPrecio.objects.create(
                            equipo=equipo,
                            precio=precio_anterior,
                        )

                    equipo.precio = precio_decimal
                    if enlace:
                        equipo.enlace_compra = enlace[:1000]
                    if thumbnail:
                        equipo.imagen_url = thumbnail[:1000]
                    equipo.tienda = tienda[:150]
                    equipo.save(update_fields=['precio', 'enlace_compra', 'imagen_url', 'tienda', 'actualizado_en'])

                    if not HistorialPrecio.objects.filter(equipo=equipo, fecha=fecha_hoy).exists():
                        HistorialPrecio.objects.create(
                            equipo=equipo,
                            precio=precio_decimal,
                        )

                return ('actualizado', False)
            else:
                return ('sin_cambio', False)

        else:
            if not dry_run:
                nuevo_equipo = Equipo.objects.create(
                    tipo=tipo_equipo,
                    marca=marca,
                    modelo=modelo,
                    procesador=specs["procesador"],
                    memoria_ram=specs["memoria_ram"],
                    almacenamiento=specs["almacenamiento"],
                    tarjeta_grafica=specs["tarjeta_grafica"],
                    tamanio_pantalla=specs["tamanio_pantalla"],
                    precio=precio_decimal,
                    tienda=tienda[:150],
                    enlace_compra=enlace[:1000] if enlace else "https://shopping.google.com",
                    imagen_url=thumbnail[:1000] if thumbnail else None,
                    ciudad="Lima",
                    departamento="Lima",
                )
                HistorialPrecio.objects.create(
                    equipo=nuevo_equipo,
                    precio=precio_decimal,
                )

            return ('creado', True)
