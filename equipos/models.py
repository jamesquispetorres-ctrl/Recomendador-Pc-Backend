"""
Modelos de la app equipos:
  - Equipo: laptop o PC de escritorio con sus especificaciones
  - HistorialPrecio: historial de precios por equipo
"""
from django.db import models


class Equipo(models.Model):
    """
    Representa un equipo (laptop o PC de escritorio) disponible en el mercado.
    """

    TIPO_CHOICES = [
        ('laptop', 'Laptop'),
        ('pc_escritorio', 'PC de Escritorio'),
    ]

    # ── Clasificación ──────────────────────────────────────────────────────────
    tipo = models.CharField(
        max_length=20,
        choices=TIPO_CHOICES,
        default='laptop',
        verbose_name='Tipo de equipo',
    )

    # ── Identificación ────────────────────────────────────────────────────────
    marca = models.CharField(max_length=100, verbose_name='Marca')
    modelo = models.CharField(max_length=200, verbose_name='Modelo')

    # ── Especificaciones técnicas ─────────────────────────────────────────────
    procesador = models.CharField(max_length=200, verbose_name='Procesador')
    memoria_ram = models.IntegerField(verbose_name='Memoria RAM (GB)')
    almacenamiento = models.CharField(
        max_length=100,
        verbose_name='Almacenamiento',
        help_text='Ej: 512GB SSD, 1TB HDD',
    )
    tarjeta_grafica = models.CharField(
        max_length=200,
        verbose_name='Tarjeta Gráfica',
        blank=True,
        default='Integrada',
    )
    tamanio_pantalla = models.FloatField(
        null=True,
        blank=True,
        verbose_name='Tamaño de Pantalla (pulgadas)',
        help_text='Opcional para PCs de escritorio',
    )

    # ── Comercial ─────────────────────────────────────────────────────────────
    precio = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Precio (COP)',
    )
    tienda = models.CharField(max_length=150, verbose_name='Tienda')
    enlace_compra = models.URLField(max_length=500, verbose_name='Enlace de Compra')

    # ── Ubicación ─────────────────────────────────────────────────────────────
    ciudad = models.CharField(max_length=100, verbose_name='Ciudad')
    departamento = models.CharField(max_length=100, verbose_name='Departamento')

    # ── Metadatos ─────────────────────────────────────────────────────────────
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Equipo'
        verbose_name_plural = 'Equipos'
        ordering = ['precio']
        unique_together = [['marca', 'modelo', 'tienda']]

    def __str__(self):
        return f"{self.marca} {self.modelo} — {self.tienda} (${self.precio:,.0f})"


class HistorialPrecio(models.Model):
    """
    Registra el historial de precios de un equipo a lo largo del tiempo.
    Se crea un registro cada vez que el scraper detecta un cambio de precio.
    """
    equipo = models.ForeignKey(
        Equipo,
        on_delete=models.CASCADE,
        related_name='historial_precios',
        verbose_name='Equipo',
    )
    precio = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Precio registrado (COP)',
    )
    fecha = models.DateField(
        auto_now_add=True,
        verbose_name='Fecha de registro',
    )

    class Meta:
        verbose_name = 'Historial de Precio'
        verbose_name_plural = 'Historial de Precios'
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.equipo} — ${self.precio:,.0f} ({self.fecha})"
