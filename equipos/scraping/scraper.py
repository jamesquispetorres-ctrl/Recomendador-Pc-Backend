import os
import sys

# Configurar Django para ejecución independiente
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
try:
    import django
    django.setup()
except Exception:
    pass

from equipos.scraping.mercadolibre import MercadoLibreClient


def ejecutar_scraping():
    """
    Instancia el cliente de Mercado Libre Perú y consulta laptops y PCs de escritorio.
    """
    cliente = MercadoLibreClient()
    print(f"=== Consultando API de Mercado Libre Perú (Sitio: {cliente.SITE_ID}) ===")
    equipos = cliente.obtener_equipos()

    print(f"\nSe obtuvieron {len(equipos)} equipos (Laptops y PCs de escritorio):\n")
    for i, eq in enumerate(equipos, 1):
        print(f"[{i}] [{eq.get('tipo', 'laptop').upper()}] {eq.get('nombre')}")
        print(f"    - Precio:         S/. {eq.get('precio'):,.2f}")
        print(f"    - Procesador:     {eq.get('procesador')}")
        print(f"    - Memoria RAM:    {eq.get('memoria_ram')} GB")
        print(f"    - Almacenamiento: {eq.get('almacenamiento')}")
        print(f"    - Tarjeta Gráfica:{eq.get('tarjeta_grafica')}")
        print(f"    - Ubicación:      {eq.get('ciudad')}, {eq.get('departamento')}")
        print(f"    - Enlace:         {eq.get('enlace')}")
        print("-" * 65)

    return equipos


if __name__ == '__main__':
    # Configurar salida UTF-8 segura en Windows
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass

    ejecutar_scraping()
