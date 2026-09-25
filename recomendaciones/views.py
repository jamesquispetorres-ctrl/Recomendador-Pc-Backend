"""
View del endpoint POST /api/recomendar/

Body esperado:
{
    "presupuesto": 3000000,
    "tipo_uso": "gaming",           // gaming|diseño|oficina|estudiante|programacion|multimedia
    "tipo_equipo": "laptop",        // laptop|pc_escritorio|ambos
    "ubicacion": {                  // opcional
        "ciudad": "Bogotá",
        "departamento": "Cundinamarca"
    },
    "con_explicacion": true         // opcional, llama a Gemini si es true
}
"""
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .ml_engine import recomendar
from .gemini_explainer import generar_explicacion

logger = logging.getLogger(__name__)

TIPOS_USO_VALIDOS = ['gaming', 'diseño', 'oficina', 'estudiante', 'programacion', 'multimedia']
TIPOS_EQUIPO_VALIDOS = ['laptop', 'pc_escritorio', 'ambos']


class RecomendarView(APIView):
    """
    POST /api/recomendar/

    Recibe parámetros del usuario, ejecuta el motor ML y retorna
    una lista de equipos recomendados con sus scores de afinidad.
    Opcionalmente incluye explicaciones generadas por Gemini.
    """

    def post(self, request):
        data = request.data

        # ── Validación de campos requeridos ───────────────────────────────────
        presupuesto = data.get('presupuesto')
        tipo_uso = data.get('tipo_uso', '').lower().strip()
        tipo_equipo = data.get('tipo_equipo', 'ambos').lower().strip()
        ubicacion = data.get('ubicacion', None)
        con_explicacion = data.get('con_explicacion', False)

        errores = {}
        if presupuesto is None:
            errores['presupuesto'] = 'Este campo es requerido.'
        else:
            try:
                presupuesto = float(presupuesto)
                if presupuesto <= 0:
                    errores['presupuesto'] = 'El presupuesto debe ser mayor a 0.'
            except (TypeError, ValueError):
                errores['presupuesto'] = 'Debe ser un número válido.'

        if not tipo_uso:
            errores['tipo_uso'] = 'Este campo es requerido.'
        elif tipo_uso not in TIPOS_USO_VALIDOS:
            errores['tipo_uso'] = (
                f"Valor inválido. Opciones: {', '.join(TIPOS_USO_VALIDOS)}"
            )

        if tipo_equipo not in TIPOS_EQUIPO_VALIDOS:
            errores['tipo_equipo'] = (
                f"Valor inválido. Opciones: {', '.join(TIPOS_EQUIPO_VALIDOS)}"
            )

        if errores:
            return Response({'errores': errores}, status=status.HTTP_400_BAD_REQUEST)

        # ── Ejecutar motor de recomendaciones ─────────────────────────────────
        try:
            resultados = recomendar(
                presupuesto=presupuesto,
                tipo_uso=tipo_uso,
                tipo_equipo=tipo_equipo,
                ubicacion=ubicacion,
            )
        except Exception as exc:
            logger.exception("Error en el motor de recomendaciones: %s", exc)
            return Response(
                {'error': 'Error interno al procesar la recomendación.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # ── Generar explicaciones con Gemini (opcional) ───────────────────────
        if con_explicacion and resultados:
            for item in resultados:
                item['explicacion'] = generar_explicacion(item, tipo_uso)

        return Response({
            'total': len(resultados),
            'presupuesto': presupuesto,
            'tipo_uso': tipo_uso,
            'tipo_equipo': tipo_equipo,
            'recomendaciones': resultados,
        }, status=status.HTTP_200_OK)
