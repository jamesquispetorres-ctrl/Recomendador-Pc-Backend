"""
Script independiente para ejecutar el scraper de laptops.

Puede ser ejecutado directamente:
    python -m equipos.scraping.scraper
o
    python equipos/scraping/scraper.py

Extrae nombre, precio, procesador, RAM, almacenamiento y enlace de producto.
"""
import json
import sys
from decimal import Decimal

from equipos.scraping.base import ScraperBase
from equipos.scraping.tiendas.tecnoshop import TecnoShopScraper


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


def ejecutar_scraping(tienda_cls=TecnoShopScraper):
    """
    Instancia el scraper y ejecuta la extracción de laptops.
    """
    scraper: ScraperBase = tienda_cls()
    print(f"=== Iniciando scraping en {scraper.tienda} ===")
    equipos = scraper.run()

    print(f"\nSe extrajeron {len(equipos)} laptops exitosamente:\n")
    for i, eq in enumerate(equipos, 1):
        print(f"[{i}] {eq.get('nombre')}")
        print(f"    - Precio:         S/. {eq.get('precio')}")
        print(f"    - Procesador:     {eq.get('procesador')}")
        print(f"    - Memoria RAM:    {eq.get('memoria_ram')} GB")
        print(f"    - Almacenamiento: {eq.get('almacenamiento')}")
        print(f"    - Enlace:         {eq.get('enlace')}")
        print("-" * 50)

    return equipos


if __name__ == '__main__':
    # Configurar salida UTF-8 segura en Windows
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass

    ejecutar_scraping()
