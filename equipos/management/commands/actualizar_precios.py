"""
Comando personalizado de Django: actualizar_precios

Consulta la API pública de Mercado Libre Perú (sitio MPE) para obtener laptops
y PCs de escritorio reales, guarda nuevos equipos en la base de datos si no existen,
y si ya existen, registra el precio actual en el modelo HistorialPrecio antes de actualizarlo.

Uso:
    python manage.py actualizar_precios
    python manage.py actualizar_precios --tienda mercadolibre
    python manage.py actualizar_precios --dry-run
"""
import logging
import sys
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from equipos.models import Equipo, HistorialPrecio
from equipos.scraping.mercadolibre import MercadoLibreClient

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

# Diccionario de fuentes disponibles
FUENTES_DISPONIBLES = {
    'mercadolibre': MercadoLibreClient,
}


class Command(BaseCommand):
    help = (
        'Obtiene laptops y PCs desde la API de Mercado Libre Perú (MPE), '
        'guarda nuevos equipos o actualiza precios registrando en HistorialPrecio.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--tienda',
            type=str,
            default=None,
            help=f"Fuente a consultar. Opciones: {', '.join(FUENTES_DISPONIBLES.keys())}",
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

        # Seleccionar qué cliente ejecutar
        if tienda_filtro:
            tienda_nombre = tienda_filtro.lower()
            if tienda_nombre not in FUENTES_DISPONIBLES:
                raise CommandError(
                    f"Tienda '{tienda_nombre}' no reconocida. Opciones disponibles: {', '.join(FUENTES_DISPONIBLES.keys())}"
                )
            fuentes_a_ejecutar = {tienda_nombre: FUENTES_DISPONIBLES[tienda_nombre]}
        else:
            fuentes_a_ejecutar = FUENTES_DISPONIBLES

        total_nuevos = 0
        total_actualizados = 0
        total_sin_cambio = 0
        total_errores = 0

        for nombre_fuente, ClaseCliente in fuentes_a_ejecutar.items():
            self.stdout.write(f"\n>>> Conectando con: {nombre_fuente.upper()} (Sitio: MPE - Perú) <<<")
            self.stdout.write("-" * 65)

            try:
                cliente = ClaseCliente()
                equipos_obtenidos = cliente.obtener_equipos()
            except Exception as exc:
                # Requisito: registrar el error en el registro de eventos sin detener el resto del proceso
                self.stdout.write(self.style.ERROR(f"Error al conectar con {nombre_fuente}: {exc}"))
                logger.error("Error al conectar con la API de %s: %s", nombre_fuente, exc, exc_info=True)
                continue

            if not equipos_obtenidos:
                self.stdout.write(self.style.WARNING(f"No se obtuvieron equipos de {nombre_fuente}."))
                continue

            for datos in equipos_obtenidos:
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

        # Resumen final
        self.stdout.write("\n" + "=" * 65)
        self.stdout.write(self.style.SUCCESS(f"Sincronización con Mercado Libre completada."))
        self.stdout.write(self.style.SUCCESS(f"  * Nuevos equipos guardados en BD:  {total_nuevos}"))
        self.stdout.write(self.style.SUCCESS(f"  * Precios actualizados en BD:      {total_actualizados}"))
        self.stdout.write(f"  * Equipos sin cambio de precio:     {total_sin_cambio}")
        if total_errores > 0:
            self.stdout.write(self.style.ERROR(f"  * Errores registrados:             {total_errores}"))

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
        tienda = datos.get('tienda') or 'Mercado Libre'
        enlace = datos.get('enlace') or ''
        precio_nuevo = Decimal(str(datos.get('precio', 0)))

        if precio_nuevo <= Decimal('0'):
            return 'sin_cambio'

        # Buscar si el equipo ya existe:
        # Primero por enlace de compra (permalink de Mercado Libre es único), luego por marca+modelo+tienda
        equipo = None
        if enlace:
            equipo = Equipo.objects.filter(enlace_compra=enlace).first()
        if not equipo:
            equipo = Equipo.objects.filter(marca__iexact=marca, modelo__iexact=modelo, tienda=tienda).first()

        if equipo:
            # ── El equipo YA EXISTE ───────────────────────────────────────────
            precio_actual = equipo.precio

            if precio_actual != precio_nuevo:
                if not dry_run:
                    # 1. Registrar el precio actual en HistorialPrecio ANTES de actualizarlo
                    HistorialPrecio.objects.create(
                        equipo=equipo,
                        precio=precio_actual,
                    )

                    # 2. Actualizar al nuevo precio y actualizar datos de contacto/enlace
                    equipo.precio = precio_nuevo
                    if enlace:
                        equipo.enlace_compra = enlace
                    if datos.get('ciudad'):
                        equipo.ciudad = datos.get('ciudad')
                    if datos.get('departamento'):
                        equipo.departamento = datos.get('departamento')

                    equipo.save(update_fields=['precio', 'enlace_compra', 'ciudad', 'departamento', 'actualizado_en'])

                cambio = precio_nuevo - precio_actual
                signo = "+" if cambio > 0 else ""
                self.stdout.write(
                    f"  [ACTUALIZADO] {equipo.marca} {equipo.modelo}\n"
                    f"     Historial guardado: S/. {precio_actual:,.2f} -> Nuevo precio: S/. {precio_nuevo:,.2f} ({signo}{cambio:,.2f})"
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
                    tamanio_pantalla=datos.get('tamanio_pantalla'),
                    precio=precio_nuevo,
                    tienda=tienda,
                    enlace_compra=enlace or 'https://www.mercadolibre.com.pe',
                    ciudad=datos.get('ciudad', 'Lima'),
                    departamento=datos.get('departamento', 'Lima'),
                )

            self.stdout.write(
                self.style.SUCCESS(
                    f"  [NUEVO EQUIPO] [{datos.get('tipo', 'laptop').upper()}] {marca} {modelo} | S/. {precio_nuevo:,.2f} | Ubicación: {datos.get('ciudad', 'Lima')}"
                )
            )
            return 'creado'
