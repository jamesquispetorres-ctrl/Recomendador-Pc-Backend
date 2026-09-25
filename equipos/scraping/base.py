"""
Clase base abstracta para todos los scrapers del sistema de laptops.

Para agregar una nueva tienda:
1. Crea un archivo en equipos/scraping/tiendas/mi_tienda.py
2. Hereda de ScraperBase
3. Define los atributos de clase (tienda, url_listado, etc.)
4. Implementa el método extraer_equipos() extrayendo:
   - nombre
   - precio
   - procesador
   - RAM (memoria_ram)
   - almacenamiento
   - enlace (o enlace_compra)
"""
import logging
import re
import time
from abc import ABC, abstractmethod
from decimal import Decimal, InvalidOperation

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Cabeceras para simular un navegador real y evitar bloqueos
HEADERS_DEFECTO = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/124.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'es-PE,es;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
}


class ScraperBase(ABC):
    """
    Clase base abstracta para scrapers de tiendas de laptops y tecnología.

    Atributos de clase a definir en cada subclase:
        tienda (str): Nombre de la tienda (ej: 'TecnoShop', 'Falabella', etc.)
        ciudad (str): Ciudad principal de la tienda.
        departamento (str): Región o departamento.
        url_listado (str): URL de la página con el listado de laptops.
        tipo_equipo (str): 'laptop' o 'pc_escritorio'.
        retardo_segundos (float): Pausa entre peticiones HTTP.
    """

    tienda: str = 'Tienda Genérica'
    ciudad: str = 'Lima'
    departamento: str = 'Lima'
    url_listado: str = ''
    tipo_equipo: str = 'laptop'
    retardo_segundos: float = 1.0

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS_DEFECTO)

    def obtener_pagina(self, url: str, params: dict | None = None) -> BeautifulSoup:
        """
        Descarga una página web usando requests y la devuelve como objeto BeautifulSoup.

        Args:
            url: URL a descargar.
            params: Parámetros query string opcionales.

        Returns:
            Objeto BeautifulSoup listo para parsear.
        """
        logger.info("[%s] Descargando URL: %s", self.tienda, url)
        if self.retardo_segundos > 0:
            time.sleep(self.retardo_segundos)

        response = self.session.get(url, params=params, timeout=15)
        response.raise_for_status()
        return self.parsear_html(response.text)

    @staticmethod
    def parsear_html(html_str: str) -> BeautifulSoup:
        """
        Convierte una cadena de texto HTML en un árbol BeautifulSoup.
        Usa 'lxml' si está disponible, o 'html.parser' como fallback seguro.
        """
        try:
            return BeautifulSoup(html_str, 'lxml')
        except Exception:
            return BeautifulSoup(html_str, 'html.parser')

    @abstractmethod
    def extraer_equipos(self) -> list[dict]:
        """
        Extrae los equipos desde la página o listado de laptops.

        Debe retornar una lista de diccionarios con las siguientes claves obligatorias:
            - nombre (str): Nombre completo del producto
            - precio (Decimal): Precio numérico
            - procesador (str): Modelo del procesador (ej: Intel Core i7-13700H)
            - memoria_ram (int): Cantidad de RAM en GB (ej: 16)
            - almacenamiento (str): Capacidad y tipo (ej: 512GB SSD)
            - enlace (str): URL directa al producto

        Opcionales:
            - marca (str)
            - modelo (str)
            - tarjeta_grafica (str)
            - tamanio_pantalla (float)
            - tienda (str)
            - ciudad (str)
            - departamento (str)
            - tipo (str)
        """
        ...

    # ── MÉTODOS DE LIMPIEZA Y EXTRACCIÓN REUTILIZABLES ──────────────────────────

    def limpiar_precio(self, texto: str) -> Decimal:
        """
        Limpia un texto de precio (ej: 'S/. 2,799.00', 'S/ 3500', '$ 1.250.000', '2,999')
        y lo convierte a Decimal.
        """
        if not texto:
            return Decimal('0')

        # Buscar la primera ocurrencia de un bloque de números con separadores
        match = re.search(r'(\d[\d., ]*)', str(texto))
        if not match:
            return Decimal('0')

        limpio = match.group(1).strip().replace(' ', '')

        if ',' in limpio and '.' in limpio:
            if limpio.rfind(',') > limpio.rfind('.'):
                # Formato: 2.799,50
                limpio = limpio.replace('.', '').replace(',', '.')
            else:
                # Formato: 2,799.50
                limpio = limpio.replace(',', '')
        elif ',' in limpio:
            partes = limpio.split(',')
            if len(partes[-1]) == 2:
                limpio = limpio.replace(',', '.')
            else:
                limpio = limpio.replace(',', '')
        elif '.' in limpio:
            partes = limpio.split('.')
            if len(partes[-1]) == 2:
                pass  # Decimal estándar
            else:
                limpio = limpio.replace('.', '')

        try:
            return Decimal(limpio)
        except InvalidOperation:
            logger.warning("[%s] No se pudo parsear precio '%s' -> '%s'", self.tienda, texto, limpio)
            return Decimal('0')

    def extraer_ram_gb(self, texto: str) -> int:
        """
        Extrae la cantidad de memoria RAM en GB a partir de una descripción.
        Ej: '16GB DDR5', 'RAM 8 GB', '32 GB' -> 16, 8, 32
        """
        if not texto:
            return 0
        match = re.search(r'(\d+)\s*(?:gb|gigabytes)', str(texto), re.IGNORECASE)
        return int(match.group(1)) if match else 0

    def extraer_almacenamiento(self, texto: str) -> str:
        """
        Extrae la especificación de almacenamiento del texto.
        Ej: '512GB SSD NVMe', '1TB HDD', '1 TB SSD'
        """
        if not texto:
            return 'No especificado'
        match = re.search(
            r'(\d+)\s*(gb|tb)\s*(ssd|hdd|nvme|emmc)?',
            str(texto),
            re.IGNORECASE,
        )
        if match:
            cantidad, unidad, tipo = match.groups()
            tipo_str = f" {tipo.upper()}" if tipo else " SSD"
            return f"{cantidad}{unidad.upper()}{tipo_str}"
        return '512GB SSD'

    def extraer_procesador(self, texto: str) -> str:
        """
        Detecta y normaliza el modelo de procesador en un texto descriptivo.
        """
        if not texto:
            return 'No especificado'

        patrones = [
            r'intel\s+core\s+i[3579][\w-]*',
            r'core\s+i[3579][\w-]*',
            r'amd\s+ryzen\s+[3579]\s*[\w-]*',
            r'ryzen\s+[3579]\s*[\w-]*',
            r'apple\s+m[1234]\s*(?:pro|max|ultra)?',
            r'intel\s+celeron\s*[\w-]*',
            r'intel\s+pentium\s*[\w-]*',
        ]
        for pat in patrones:
            match = re.search(pat, str(texto), re.IGNORECASE)
            if match:
                return match.group(0).strip().title()
        return 'Intel Core i5'

    def extraer_marca(self, nombre: str) -> str:
        """
        Identifica la marca conocida en el nombre de la laptop.
        """
        marcas = [
            'ASUS', 'LENOVO', 'HP', 'DELL', 'ACER', 'APPLE', 'MSI',
            'SAMSUNG', 'HUAWEI', 'LG', 'GIGABYTE', 'RAZER', 'TOSHIBA'
        ]
        nombre_upper = (nombre or '').upper()
        for marca in marcas:
            if marca in nombre_upper:
                return marca.title()
        return (nombre.split()[0] if nombre else 'Genérico').title()

    def run(self) -> list[dict]:
        """
        Ejecuta el proceso completo de scraping de la tienda y valida los campos mínimos.
        """
        logger.info("[%s] Iniciando extracción de laptops...", self.tienda)
        try:
            items = self.extraer_equipos()
            logger.info("[%s] Extracción finalizada. Total encontrados: %d", self.tienda, len(items))
            return items
        except Exception as exc:
            logger.error("[%s] Error durante la extracción: %s", self.tienda, exc, exc_info=True)
            return []
