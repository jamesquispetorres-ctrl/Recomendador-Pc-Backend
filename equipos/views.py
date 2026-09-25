"""
Views de la app equipos — ViewSet para CRUD completo vía API REST.
"""
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Equipo, HistorialPrecio
from .serializers import EquipoSerializer, EquipoListSerializer, HistorialPrecioSerializer


class EquipoViewSet(viewsets.ModelViewSet):
    """
    ViewSet completo para el modelo Equipo.

    Endpoints generados automáticamente:
        GET    /api/equipos/           → lista todos los equipos
        POST   /api/equipos/           → crea un equipo
        GET    /api/equipos/{id}/      → detalle de un equipo
        PUT    /api/equipos/{id}/      → actualiza un equipo
        PATCH  /api/equipos/{id}/      → actualización parcial
        DELETE /api/equipos/{id}/      → elimina un equipo
        GET    /api/equipos/{id}/historial/ → historial de precios
    """
    queryset = Equipo.objects.all().order_by('precio')
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['marca', 'modelo', 'procesador', 'ciudad', 'departamento', 'tienda']
    ordering_fields = ['precio', 'memoria_ram', 'creado_en']

    def get_serializer_class(self):
        """Usa serializer reducido para listados y completo para detalle."""
        if self.action == 'list':
            return EquipoListSerializer
        return EquipoSerializer

    def get_queryset(self):
        """Permite filtrar por tipo, ciudad, departamento y rango de precio."""
        qs = super().get_queryset()
        tipo = self.request.query_params.get('tipo')
        ciudad = self.request.query_params.get('ciudad')
        departamento = self.request.query_params.get('departamento')
        precio_min = self.request.query_params.get('precio_min')
        precio_max = self.request.query_params.get('precio_max')

        if tipo:
            qs = qs.filter(tipo=tipo)
        if ciudad:
            qs = qs.filter(ciudad__icontains=ciudad)
        if departamento:
            qs = qs.filter(departamento__icontains=departamento)
        if precio_min:
            qs = qs.filter(precio__gte=precio_min)
        if precio_max:
            qs = qs.filter(precio__lte=precio_max)

        return qs

    @action(detail=True, methods=['get'], url_path='historial')
    def historial(self, request, pk=None):
        """Retorna el historial de precios de un equipo específico."""
        equipo = self.get_object()
        historial = equipo.historial_precios.all()
        serializer = HistorialPrecioSerializer(historial, many=True)
        return Response(serializer.data)
