"""
Módulo de scraping y clientes de tiendas para la app 'equipos'.
Permite extraer laptops y computadoras desde la API pública de Mercado Libre Perú (MPE)
y otras tiendas estructuradas.
"""
from .base import ScraperBase
from .mercadolibre import MercadoLibreClient

__all__ = ['ScraperBase', 'MercadoLibreClient']
