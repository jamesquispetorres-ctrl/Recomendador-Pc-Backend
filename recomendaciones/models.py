"""
Modelo Valoracion de la app recomendaciones.
"""
from django.db import models


class Valoracion(models.Model):
    """
    Permite a los usuarios calificar si una recomendación fue útil.
    Se relaciona con una recomendación mediante un identificador de sesión.
    """
    # Identificador de la sesión/recomendación (UUID o string arbitrario)
    sesion_id = models.CharField(
        max_length=100,
        verbose_name='ID de Sesión',
        help_text='Identificador único de la sesión de recomendación',
    )
    # Equipo recomendado que se está valorando
    equipo = models.ForeignKey(
        'equipos.Equipo',
        on_delete=models.CASCADE,
        related_name='valoraciones',
        verbose_name='Equipo valorado',
    )
    usuario = models.CharField(
        max_length=150,
        verbose_name='Usuario (nombre o email)',
        blank=True,
        default='Anónimo',
    )
    util = models.BooleanField(
        verbose_name='¿Fue útil esta recomendación?',
    )
    comentario = models.TextField(
        blank=True,
        verbose_name='Comentario adicional',
    )
    fecha = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de valoración',
    )

    class Meta:
        verbose_name = 'Valoración'
        verbose_name_plural = 'Valoraciones'
        ordering = ['-fecha']

    def __str__(self):
        util_str = '👍 Útil' if self.util else '👎 No útil'
        return f"{util_str} — {self.equipo} ({self.fecha.date()})"
