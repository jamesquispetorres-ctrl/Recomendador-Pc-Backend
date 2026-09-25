"""
URL configuration del proyecto Sistema de Recomendación de Laptops.
"""
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.utils import timezone

from rest_framework.routers import DefaultRouter
from equipos.views import EquipoViewSet
from recomendaciones.views import RecomendarView

# ─── Router DRF ──────────────────────────────────────────────────────────────
router = DefaultRouter()
router.register(r'equipos', EquipoViewSet, basename='equipo')


def health_check(request):
    """
    Endpoint de salud para monitoreo con UptimeRobot.
    GET /api/health/  →  {"status": "ok", "timestamp": "..."}
    """
    return JsonResponse({
        'status': 'ok',
        'timestamp': timezone.now().isoformat(),
        'version': '1.0.0',
    })


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api/recomendar/', RecomendarView.as_view(), name='recomendar'),
    path('api/health/', health_check, name='health'),
    path('health/', health_check, name='health-root'),
]

