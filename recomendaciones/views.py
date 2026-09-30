"""
Views de la app recomendaciones:
  - RecomendarView: POST /api/recomendar/  → motor ML + Gemini
  - CatalogoView:   POST /api/catalogo/    → todos los equipos con score + Gemini
  - ChatView:       POST /api/chat/        → conversación libre con Gemini AI
"""
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .ml_engine import recomendar, recomendar_catalogo
from .gemini_explainer import generar_explicacion, chat_gemini

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
        con_explicacion = True  # Siempre generar explicación (con fallback si Gemini no está)

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

        # ── Generar explicaciones (Gemini si disponible, fallback automático) ──
        for item in resultados:
            try:
                item['explicacion'] = generar_explicacion(item, tipo_uso)
            except Exception:
                item['explicacion'] = None

        return Response({
            'total': len(resultados),
            'presupuesto': presupuesto,
            'tipo_uso': tipo_uso,
            'tipo_equipo': tipo_equipo,
            'recomendaciones': resultados,
        }, status=status.HTTP_200_OK)


class CatalogoView(APIView):
    """
    POST /api/catalogo/

    Retorna TODOS los equipos del catálogo ordenados por score de afinidad,
    sin filtro de presupuesto. Ideal para exploración y comparación.
    """

    def post(self, request):
        data = request.data
        tipo_uso = data.get('tipo_uso', 'oficina').lower().strip()
        tipo_equipo = data.get('tipo_equipo', 'ambos').lower().strip()
        con_explicacion = data.get('con_explicacion', True)

        if tipo_uso not in TIPOS_USO_VALIDOS:
            tipo_uso = 'oficina'
        if tipo_equipo not in TIPOS_EQUIPO_VALIDOS:
            tipo_equipo = 'ambos'

        try:
            resultados = recomendar_catalogo(
                tipo_uso=tipo_uso,
                tipo_equipo=tipo_equipo,
            )
        except Exception as exc:
            logger.exception("Error al obtener catálogo: %s", exc)
            return Response(
                {'error': 'Error interno al obtener el catálogo.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Gemini solo para los primeros 5 para no exceder cuotas
        if con_explicacion and resultados:
            for item in resultados[:5]:
                item['explicacion'] = generar_explicacion(item, tipo_uso)

        return Response({
            'total': len(resultados),
            'tipo_uso': tipo_uso,
            'tipo_equipo': tipo_equipo,
            'recomendaciones': resultados,
        }, status=status.HTTP_200_OK)


class ChatView(APIView):
    """
    POST /api/chat/

    Recibe un mensaje del usuario y contexto de equipos,
    y retorna una respuesta conversacional de Gemini AI.

    Body esperado:
    {
        "mensaje": "¿Cuál laptop es mejor para gaming?",
        "tipo_uso": "gaming",
        "tipo_equipo": "laptop",
        "equipos": [ {...}, {...} ]   // lista de equipos del catálogo
    }
    """

    def post(self, request):
        data = request.data
        mensaje = data.get('mensaje', '').strip()
        tipo_uso = data.get('tipo_uso', 'general').strip()
        tipo_equipo = data.get('tipo_equipo', 'laptop').strip()
        equipos = data.get('equipos', [])

        if not mensaje:
            return Response(
                {'error': 'El campo "mensaje" es requerido.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            respuesta = chat_gemini(
                mensaje=mensaje,
                tipo_uso=tipo_uso,
                tipo_equipo=tipo_equipo,
                equipos=equipos,
            )
        except Exception as exc:
            logger.exception("Error en ChatView Gemini: %s", exc)
            return Response(
                {'error': 'Error al procesar el mensaje con Gemini AI.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response({'respuesta': respuesta}, status=status.HTTP_200_OK)
