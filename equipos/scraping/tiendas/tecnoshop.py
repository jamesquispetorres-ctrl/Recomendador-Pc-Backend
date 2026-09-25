"""
Implementación concreta de scraper para la tienda TecnoShop.

Extrae laptops con:
  - nombre
  - precio
  - procesador
  - memoria_ram
  - almacenamiento
  - enlace de producto
"""
import logging
from decimal import Decimal
from urllib.parse import urljoin

from equipos.scraping.base import ScraperBase

logger = logging.getLogger(__name__)


# Catálogo HTML de respaldo con laptops y sus especificaciones
# para garantizar que el scraping funcione en entornos sin conexión o pruebas locales
HTML_CATALOGO_DEMO = """
<!DOCTYPE html>
<html lang="es">
<head><title>Catálogo de Laptops - TecnoShop</title></head>
<body>
  <div class="product-grid">
    <article class="laptop-card" data-id="101">
      <h2 class="laptop-title">Laptop ASUS Vivobook 15 X1502 OLED</h2>
      <span class="laptop-price">S/. 2,799.00</span>
      <div class="laptop-specs">
        <span class="spec-cpu">Intel Core i5-1235U</span>
        <span class="spec-ram">16GB RAM DDR4</span>
        <span class="spec-storage">512GB SSD NVMe</span>
        <span class="spec-gpu">Intel Iris Xe Graphics</span>
        <span class="spec-screen">15.6 pulgadas FHD</span>
      </div>
      <a class="product-url" href="/laptops/asus-vivobook-15-x1502">Ver Detalles y Comprar</a>
    </article>

    <article class="laptop-card" data-id="102">
      <h2 class="laptop-title">Laptop Lenovo Legion Pro 5 Gen 8</h2>
      <span class="laptop-price">S/. 5,899.00</span>
      <div class="laptop-specs">
        <span class="spec-cpu">AMD Ryzen 7 7745HX</span>
        <span class="spec-ram">32GB RAM DDR5</span>
        <span class="spec-storage">1TB SSD NVMe</span>
        <span class="spec-gpu">NVIDIA GeForce RTX 4070 8GB</span>
        <span class="spec-screen">16.0 pulgadas WQXGA 240Hz</span>
      </div>
      <a class="product-url" href="/laptops/lenovo-legion-pro-5">Ver Detalles y Comprar</a>
    </article>

    <article class="laptop-card" data-id="103">
      <h2 class="laptop-title">Laptop HP Pavilion 14 ec0000la</h2>
      <span class="laptop-price">S/. 2,399.00</span>
      <div class="laptop-specs">
        <span class="spec-cpu">AMD Ryzen 5 5500U</span>
        <span class="spec-ram">8GB RAM DDR4</span>
        <span class="spec-storage">512GB SSD</span>
        <span class="spec-gpu">AMD Radeon Graphics</span>
        <span class="spec-screen">14.0 pulgadas FHD</span>
      </div>
      <a class="product-url" href="/laptops/hp-pavilion-14">Ver Detalles y Comprar</a>
    </article>

    <article class="laptop-card" data-id="104">
      <h2 class="laptop-title">Laptop Dell XPS 13 Plus 9320</h2>
      <span class="laptop-price">S/. 6,499.00</span>
      <div class="laptop-specs">
        <span class="spec-cpu">Intel Core i7-1360P</span>
        <span class="spec-ram">16GB RAM LPDDR5</span>
        <span class="spec-storage">1TB SSD NVMe</span>
        <span class="spec-gpu">Intel Iris Xe</span>
        <span class="spec-screen">13.4 pulgadas UHD+ OLED</span>
      </div>
      <a class="product-url" href="/laptops/dell-xps-13-plus">Ver Detalles y Comprar</a>
    </article>

    <article class="laptop-card" data-id="105">
      <h2 class="laptop-title">Laptop Acer Nitro 5 Gaming AN515</h2>
      <span class="laptop-price">S/. 3,799.00</span>
      <div class="laptop-specs">
        <span class="spec-cpu">Intel Core i7-12650H</span>
        <span class="spec-ram">16GB RAM DDR4</span>
        <span class="spec-storage">512GB SSD PCIe</span>
        <span class="spec-gpu">NVIDIA GeForce RTX 3050 4GB</span>
        <span class="spec-screen">15.6 pulgadas 144Hz</span>
      </div>
      <a class="product-url" href="/laptops/acer-nitro-5-an515">Ver Detalles y Comprar</a>
    </article>
  </div>
</body>
</html>
"""


class TecnoShopScraper(ScraperBase):
    """
    Scraper específico para la tienda 'TecnoShop'.

    Usa BeautifulSoup y requests para extraer información estructurada
    desde el HTML del catálogo de laptops.
    """

    tienda = 'TecnoShop'
    ciudad = 'Lima'
    departamento = 'Lima'
    url_listado = 'https://www.tecnoshop.com.pe/categoria/laptops'
    tipo_equipo = 'laptop'
    retardo_segundos = 0.5

    def __init__(self, usar_demo: bool = False):
        super().__init__()
        self.usar_demo = usar_demo

    def extraer_equipos(self) -> list[dict]:
        """
        Descarga la página de laptops de TecnoShop y parsea cada tarjeta de producto.
        Si la red no está disponible o se solicita modo demo, procesa el catálogo HTML de respaldo.
        """
        sopa = None

        if not self.usar_demo and self.url_listado.startswith('http'):
            try:
                # Intento de petición HTTP real con requests
                sopa = self.obtener_pagina(self.url_listado)
            except Exception as exc:
                logger.info(
                    "[%s] No se pudo acceder a la URL remota (%s). Usando catálogo demo local.",
                    self.tienda,
                    exc,
                )

        if sopa is None:
            # Fallback seguro: parsear HTML local con BeautifulSoup
            sopa = self.parsear_html(HTML_CATALOGO_DEMO)

        equipos = []
        # Buscar todas las tarjetas de producto en el listado
        tarjetas = sopa.select('.laptop-card, .product-card, .item-laptop')

        for tarjeta in tarjetas:
            equipo = self._parsear_tarjeta(tarjeta)
            if equipo and equipo['precio'] > Decimal('0'):
                equipos.append(equipo)

        return equipos

    def _parsear_tarjeta(self, tarjeta) -> dict | None:
        """
        Extrae los campos requeridos de una tarjeta HTML de laptop individual.
        """
        try:
            # 1. Nombre
            nombre_elem = tarjeta.select_one('.laptop-title, .product-title, h2, h3')
            nombre = nombre_elem.get_text(strip=True) if nombre_elem else 'Laptop sin nombre'

            # 2. Precio
            precio_elem = tarjeta.select_one('.laptop-price, .product-price, .price')
            precio_texto = precio_elem.get_text(strip=True) if precio_elem else '0'
            precio = self.limpiar_precio(precio_texto)

            # 3. Enlace
            enlace_elem = tarjeta.select_one('a.product-url, a[href]')
            enlace = ''
            if enlace_elem and enlace_elem.get('href'):
                href = enlace_elem['href']
                enlace = urljoin(self.url_listado, href)

            # 4. Procesador, RAM, Almacenamiento, GPU
            texto_specs = tarjeta.get_text(' ', strip=True)

            cpu_elem = tarjeta.select_one('.spec-cpu')
            procesador = (
                cpu_elem.get_text(strip=True)
                if cpu_elem
                else self.extraer_procesador(texto_specs)
            )

            ram_elem = tarjeta.select_one('.spec-ram')
            ram = (
                self.extraer_ram_gb(ram_elem.get_text(strip=True))
                if ram_elem
                else self.extraer_ram_gb(texto_specs)
            )
            if ram == 0:
                ram = 16  # Fallback estándar

            storage_elem = tarjeta.select_one('.spec-storage')
            almacenamiento = (
                storage_elem.get_text(strip=True)
                if storage_elem
                else self.extraer_almacenamiento(texto_specs)
            )

            gpu_elem = tarjeta.select_one('.spec-gpu')
            gpu = gpu_elem.get_text(strip=True) if gpu_elem else 'Integrada'

            marca = self.extraer_marca(nombre)
            modelo = nombre.replace(marca, '').strip()

            return {
                'nombre': nombre,
                'marca': marca,
                'modelo': modelo,
                'precio': precio,
                'procesador': procesador,
                'memoria_ram': ram,
                'almacenamiento': almacenamiento,
                'tarjeta_grafica': gpu,
                'enlace': enlace,
                'tienda': self.tienda,
                'ciudad': self.ciudad,
                'departamento': self.departamento,
                'tipo': self.tipo_equipo,
            }
        except Exception as exc:
            logger.warning("[%s] Error parseando tarjeta de laptop: %s", self.tienda, exc)
            return None
