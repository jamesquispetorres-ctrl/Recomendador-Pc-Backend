"""
Comando personalizado de Django: actualizar_precios

Consulta la API de Google Shopping a través de SerpApi (país Perú, gl=pe, hl=es)
para obtener laptops y PCs de escritorio reales, recorriendo términos de búsqueda uno por uno.
Guarda nuevos equipos en la base de datos y actualiza precios e historial en HistorialPrecio.

Uso:
    python manage.py actualizar_precios
    python manage.py actualizar_precios --dry-run
"""
import logging
import sys

from django.core.management.base import BaseCommand
from equipos.serpapi_client import SerpApiClient, BUSQUEDAS_PERU_DEFAULT

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


class Command(BaseCommand):
    help = (
        'Obtiene laptops y PCs desde Google Shopping Perú a través de SerpApi, '
        'recorriendo los términos de búsqueda uno por uno y registrando precios en BD.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--term',
            type=str,
            default=None,
            help='Término específico de búsqueda para consultar en SerpApi.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            default=False,
            help='Simula la ejecución sin realizar escrituras en la base de datos.',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run')
        termino_filtro = options.get('term')

        if dry_run:
            self.stdout.write(self.style.WARNING('[DRY-RUN] Modo simulación activo: no se guardarán cambios en la BD.'))

        terminos_a_buscar = [termino_filtro] if termino_filtro else BUSQUEDAS_PERU_DEFAULT

        client = SerpApiClient()

        busquedas_realizadas = 0
        nuevos_guardados = 0
        productos_actualizados = 0
        productos_sin_cambio = 0
        advertencias_registradas = 0

        self.stdout.write(self.style.MIGRATE_HEADING("=== ACTUALIZACIÓN DE PRECIOS CON GOOGLE SHOPPING (SERPAPI PERÚ) ==="))

        for query in terminos_a_buscar:
            self.stdout.write(f"\n>>> Ejecutando búsqueda en Google Shopping: '{query}' (gl=pe, hl=es) <<<")
            self.stdout.write("-" * 70)

            try:
                results = client.buscar_google_shopping(query)
                busquedas_realizadas += 1
                self.stdout.write(self.style.SUCCESS(f"  ✓ Búsqueda exitosa. Se obtuvieron {len(results)} productos."))
            except Exception as exc:
                advertencias_registradas += 1
                msg_warning = f"  ⚠️ [ADVERTENCIA] Falló la búsqueda '{query}' o se agotó la cuota mensual de SerpApi: {exc}"
                self.stdout.write(self.style.WARNING(msg_warning))
                logger.warning("Advertencia SerpApi en termino '%s': %s", query, exc)
                continue

            for item in results:
                try:
                    estado, es_nuevo = client.guardar_o_actualizar_producto(item, query, dry_run=dry_run)
                    if estado == 'creado':
                        nuevos_guardados += 1
                        titulo = item.get("title") or item.get("name")
                        self.stdout.write(self.style.SUCCESS(f"    [NUEVO] {titulo}"))
                    elif estado == 'actualizado':
                        productos_actualizados += 1
                        titulo = item.get("title") or item.get("name")
                        self.stdout.write(f"    [ACTUALIZADO] {titulo}")
                    else:
                        productos_sin_cambio += 1
                except Exception as exc_prod:
                    logger.error("Error al procesar producto de SerpApi: %s", exc_prod, exc_info=True)
                    self.stdout.write(self.style.ERROR(f"    [ERROR] No se pudo procesar producto: {exc_prod}"))

        # Resumen en consola con las métricas requeridas
        self.stdout.write("\n" + "=" * 70)
        self.stdout.write(self.style.SUCCESS("✓ Proceso de actualización finalizado con éxito."))
        self.stdout.write(self.style.SUCCESS(f"  * Total de búsquedas realizadas: {busquedas_realizadas}"))
        self.stdout.write(self.style.SUCCESS(f"  * Productos nuevos guardados:     {nuevos_guardados}"))
        self.stdout.write(f"  * Productos actualizados:         {productos_actualizados}")
        self.stdout.write(f"  * Productos sin cambios:          {productos_sin_cambio}")
        if advertencias_registradas > 0:
            self.stdout.write(self.style.WARNING(f"  * Advertencias / Fallos:          {advertencias_registradas}"))
