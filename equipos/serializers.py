"""
Serializers de la app equipos.
"""
from rest_framework import serializers
from .models import Equipo, HistorialPrecio


class HistorialPrecioSerializer(serializers.ModelSerializer):
    class Meta:
        model = HistorialPrecio
        fields = ['id', 'precio', 'fecha']


class EquipoSerializer(serializers.ModelSerializer):
    """
    Serializer completo para el modelo Equipo.
    Incluye historial de precios como campo anidado (solo lectura).
    """
    historial_precios = HistorialPrecioSerializer(many=True, read_only=True)

    class Meta:
        model = Equipo
        fields = [
            'id',
            'tipo',
            'marca',
            'modelo',
            'procesador',
            'memoria_ram',
            'almacenamiento',
            'tarjeta_grafica',
            'tamanio_pantalla',
            'precio',
            'tienda',
            'enlace_compra',
            'ciudad',
            'departamento',
            'historial_precios',
            'creado_en',
            'actualizado_en',
        ]
        read_only_fields = ['id', 'creado_en', 'actualizado_en', 'historial_precios']


class EquipoListSerializer(serializers.ModelSerializer):
    """
    Serializer reducido para listados (sin historial para mejor rendimiento).
    """
    class Meta:
        model = Equipo
        fields = [
            'id', 'tipo', 'marca', 'modelo', 'procesador',
            'memoria_ram', 'almacenamiento', 'tarjeta_grafica',
            'tamanio_pantalla', 'precio', 'tienda', 'enlace_compra',
            'ciudad', 'departamento',
        ]
