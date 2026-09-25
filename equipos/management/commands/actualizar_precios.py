"""
Comando personalizado de Django: actualizar_precios

Ejecuta el scraping de tiendas de laptops registradas, guarda los nuevos
equipos en la base de datos si no existen, y si ya existen, registra el
precio actual en el modelo HistorialPrecio antes de actualizarlo.

Uso:
    python manage.py actualizar_precios
    python manage.py actualizar_precios --tienda tecnoshop
    python manage.py actualizar_precios --dry-run
"""
import logging
import sys
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from equipos.models import Equipo, HistorialPrecio
from equipos.scraping.tiendas.tecnoshop import TecnoShopScraper

logger = logging.getLogger(__name__)

# Configurar salida segura en Windows para evitar UnicodeEncodeError
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
if hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Diccionario de scrapers disponibles para fácil extensión con nuevas tiendas
SCRAPERS_DISPONIBLES = {
    'tecnoshop': TecnoShopScraper,
    # Para agregar una nueva tienda en el futuro:
    # 1. Crear equipos/scraping/tiendas/mi_tienda.py heredando de ScraperBase
    # 2. Registrar aquí: 'mi_tienda': MiTiendaScraper
}


class Command(BaseCommand):
    help = (
        'Ejecuta el scraping de tiendas, guarda nuevos equipos en la BD '
        'y registra el precio anterior en HistorialPrecio si ya existen.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--tienda',
            type=str,
            default=None,
            help=f"Ejecutar solo una tienda específica. Opciones: {', '.join(SCRAPERS_DISPONIBLES.keys())}",
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            default=False,
            help='Simula la ejecución sin realizar escrituras en la base de datos.',
        )

    def handle(self, *args, **options):
        tienda_filtro = options.get('tienda')
        dry_run = options.get('dry_run')

        if dry_run:
            self.stdout.write(self.style.WARNING('[DRY-RUN] Modo simulación activo: no se guardarán cambios en la BD.'))

        # Seleccionar qué scrapers ejecutar
        if tienda_filtro:
            tienda_nombre = tienda_filtro.lower()
            if tienda_nombre not in SCRAPERS_DISPONIBLES:
                raise CommandError(
                    f"Tienda '{tienda_nombre}' no reconocida. Opciones disponibles: {', '.join(SCRAPERS_DISPONIBLES.keys())}"
                )
            scrapers_a_ejecutar = {tienda_nombre: SCRAPERS_DISPONIBLES[tienda_nombre]}
        else:
            scrapers_a_ejecutar = SCRAPERS_DISPONIBLES

        total_nuevos = 0
        total_actualizados = 0
        total_sin_cambio = 0
        total_errores = 0

        for nombre_tienda, ClaseScraper in scrapers_a_ejecutar.items():
            self.stdout.write(f"\n>>> Iniciando scraping para tienda: {nombre_tienda.upper()} <<<")
            self.stdout.write("-" * 60)

            try:
                scraper = ClaseScraper()
                equipos_scrapeados = scraper.run()
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f"Error al ejecutar scraper {nombre_tienda}: {exc}"))
                logger.error("Error al ejecutar scraper %s: %s", nombre_tienda, exc, exc_info=True)
                continue

            if not equipos_scrapeados:
                self.stdout.write(self.style.WARNING(f"No se obtuvieron equipos de {nombre_tienda}."))
                continue

            for datos in equipos_scrapeados:
                try:
                    resultado = self._procesar_equipo(datos, dry_run)
                    if resultado == 'creado':
                        total_nuevos += 1
                    elif resultado == 'actualizado':
                        total_actualizados += 1
                    elif resultado == 'sin_cambio':
                        total_sin_cambio += 1
                except Exception as exc:
                    total_errores += 1
                    logger.error("Error al procesar equipo %s: %s", datos.get('nombre'), exc, exc_info=True)
                    self.stdout.write(self.style.ERROR(f"  [ERROR] {datos.get('nombre')} -> {exc}"))

        # Resumen de resultados
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS(f"Scraping completado."))
        self.stdout.write(self.style.SUCCESS(f"  * Nuevos equipos guardados:    {total_nuevos}"))
        self.stdout.write(self.style.SUCCESS(f"  * Precios actualizados en BD:  {total_actualizados}"))
        self.stdout.write(f"  * Equipos sin cambio de precio: {total_sin_cambio}")
        if total_errores > 0:
            self.stdout.write(self.style.ERROR(f"  * Errores encontrados:         {total_errores}"))

    @transaction.atomic
    def _procesar_equipo(self, datos: dict, dry_run: bool) -> str:
        """
        Guarda un nuevo equipo en la base de datos si no existe.
        Si ya existe, registra el precio actual en HistorialPrecio antes de actualizarlo.

        Returns:
            'creado' | 'actualizado' | 'sin_cambio'
        """
        marca = datos.get('marca') or 'Genérico'
        modelo = datos.get('modelo') or datos.get('nombre', 'Modelo Desconocido')
        tienda = datos.get('tienda') or 'TecnoShop'
        enlace = datos.get('enlace') or ''
        precio_nuevo = Decimal(str(datos.get('precio', 0)))

        if precio_nuevo <= Decimal('0'):
            return 'sin_cambio'

        # Buscar si el equipo ya existe: primero por marca+modelo+tienda, o por enlace_compra
        equipo = None
        if enlace:
            equipo = Equipo.objects.filter(enlace_compra=enlace).first()
        if not equipo:
            equipo = Equipo.objects.filter(marca__iexact=marca, modelo__iexact=modelo, tienda__iexact=tienda).first()

        if equipo:
            # ── El equipo YA EXISTE ───────────────────────────────────────────
            precio_actual = equipo.precio

            if precio_actual != precio_nuevo:
                if not dry_run:
                    # 1. Registrar el precio actual en el modelo HistorialPrecio ANTES de actualizarlo
                    HistorialPrecio.objects.create(
                        equipo=equipo,
                        precio=precio_actual,
                    )

                    # 2. Actualizar al nuevo precio
                    equipo.precio = precio_nuevo
                    # Opcionalmente refrescar especificaciones si se obtuvieron
                    if datos.get('procesador') and datos.get('procesador') != 'No especificado':
                        equipo.procesador = datos.get('procesador')
                    if datos.get('memoria_ram'):
                        equipo.memoria_ram = datos.get('memoria_ram')
                    if datos.get('almacenamiento') and datos.get('almacenamiento') != 'No especificado':
                        equipo.almacenamiento = datos.get('almacenamiento')
                    if enlace:
                        equipo.enlace_compra = enlace

                    equipo.save()

                cambio = precio_nuevo - precio_actual
                signo = "+" if cambio > 0 else ""
                self.stdout.write(
                    f"  [ACTUALIZADO] {equipo.marca} {equipo.modelo}\n"
                    f"     Historial registrado: S/. {precio_actual:,.2f} -> Nuevo precio: S/. {precio_nuevo:,.2f} ({signo}{cambio:,.2f})"
                )
                return 'actualizado'
            else:
                self.stdout.write(f"  [SIN CAMBIO] {equipo.marca} {equipo.modelo} - Precio idéntico (S/. {precio_actual:,.2f})")
                return 'sin_cambio'

        else:
            # ── El equipo NO EXISTE: crear nuevo ──────────────────────────────
            if not dry_run:
                Equipo.objects.create(
                    tipo=datos.get('tipo', 'laptop'),
                    marca=marca,
                    modelo=modelo,
                    procesador=datos.get('procesador', 'Intel Core i5'),
                    memoria_ram=datos.get('memoria_ram', 16),
                    almacenamiento=datos.get('almacenamiento', '512GB SSD'),
                    tarjeta_grafica=datos.get('tarjeta_grafica', 'Integrada'),
                    tamanio_pantalla=datos.get('tamanio_pantalla', 15.6),
                    precio=precio_nuevo,
                    tienda=tienda,
                    enlace_compra=enlace or f"https://tienda.com/{marca.lower()}-{modelo.lower()}",
                    ciudad=datos.get('ciudad', 'Lima'),
                    departamento=datos.get('departamento', 'Lima'),
                )

            self.stdout.write(
                self.style.SUCCESS(
                    f"  [NUEVO EQUIPO] {marca} {modelo} | S/. {precio_nuevo:,.2f} | {datos.get('procesador')} | {datos.get('memoria_ram')}GB RAM"
                )
            )
            return 'creado'
