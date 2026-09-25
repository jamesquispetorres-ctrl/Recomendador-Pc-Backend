"""
Módulo de scraping para la app 'equipos'.
Permite extraer laptops desde páginas web estructuradas usando BeautifulSoup y requests.
"""
from .base import ScraperBase
from .tiendas.tecnoshop import TecnoShopScraper

__all__ = ['ScraperBase', 'TecnoShopScraper']
