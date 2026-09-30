"""
URL configuration del proyecto Sistema de Recomendación de Laptops.
"""
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.utils import timezone

from rest_framework.routers import DefaultRouter
from equipos.views import EquipoViewSet
from recomendaciones.views import RecomendarView, CatalogoView, ChatView

# ─── Router DRF ──────────────────────────────────────────────────────────────
router = DefaultRouter()
router.register(r'equipos', EquipoViewSet, basename='equipo')


from django.db import connection


def health_check(request):
    """
    Endpoint de salud para monitoreo con UptimeRobot.
    Realiza una consulta SELECT 1 para mantener despierto tanto el Web Service
    como la base de datos PostgreSQL en Render.
    GET /api/health/  →  {"status": "ok", "database": "ok", "timestamp": "..."}
    """
    db_ok = True
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1;")
    except Exception:
        db_ok = False

    return JsonResponse({
        'status': 'ok' if db_ok else 'degraded',
        'database': 'connected' if db_ok else 'disconnected',
        'timestamp': timezone.now().isoformat(),
        'version': '1.0.0',
    }, status=200 if db_ok else 503)


def mercadolibre_callback(request):
    """
    Endpoint temporal de redirección para capturar el código OAuth de Mercado Libre.
    GET /api/auth/mercadolibre/callback/?code=TG-66f8...
    """
    from django.http import HttpResponse
    from equipos.scraping.ml_auth import canjear_codigo_por_token, get_ml_credentials

    codigo = request.GET.get('code')
    error = request.GET.get('error')

    if error:
        return HttpResponse(f"""
        <html><body style="font-family:sans-serif; background:#0b1120; color:#f87171; padding:40px; text-align:center;">
            <h2>❌ Acceso denegado por Mercado Libre</h2>
            <p>Error: {error}</p>
        </body></html>
        """, status=400)

    if not codigo:
        return HttpResponse("""
        <html><body style="font-family:sans-serif; background:#0b1120; color:#e2e8f0; padding:40px; text-align:center;">
            <h2>⚠️ No se recibió el código de autorización</h2>
            <p>Asegúrate de iniciar el flujo desde la URL de autorización.</p>
        </body></html>
        """, status=400)

    try:
        creds = get_ml_credentials()
        # La URI de redirección debe coincidir con la petición actual
        redirect_uri = request.build_absolute_uri(request.path)
        tokens = canjear_codigo_por_token(
            codigo=codigo,
            client_id=creds['client_id'],
            client_secret=creds['client_secret'],
            redirect_uri=redirect_uri,
        )
        return HttpResponse(f"""
        <html><body style="font-family:sans-serif; background:#0b1120; color:#e2e8f0; padding:50px; text-align:center;">
            <div style="max-width:550px; margin:0 auto; background:#111d35; border:1px solid rgba(16,185,129,0.4); border-radius:16px; padding:30px; box-shadow:0 10px 40px rgba(0,0,0,0.5);">
                <h1 style="color:#10b981; font-size:1.8rem; margin-bottom:12px;">✅ ¡Vinculación Exitosa!</h1>
                <p style="color:#94a3b8; font-size:1rem; line-height:1.5;">
                    Tus credenciales (<strong>Access Token</strong> y <strong>Refresh Token</strong>) se han guardado automáticamente en el archivo <code>.env</code>.
                </p>
                <div style="background:rgba(255,255,255,0.05); padding:12px; border-radius:8px; margin:20px 0; font-size:0.85rem; color:#cbd5e1;">
                    User ID: <strong>{tokens.get('user_id')}</strong> · Expira en: {tokens.get('expires_in', 21600) // 3600} horas
                </div>
                <p style="color:#38bdf8; font-weight:600;">
                    Ya puedes cerrar esta pestaña y ejecutar en tu terminal:<br>
                    <code style="background:#000; padding:6px 12px; border-radius:6px; display:inline-block; margin-top:10px; color:#facc15;">python manage.py actualizar_precios</code>
                </p>
            </div>
        </body></html>
        """)
    except Exception as exc:
        return HttpResponse(f"""
        <html><body style="font-family:sans-serif; background:#0b1120; color:#ef4444; padding:40px; text-align:center;">
            <h2>❌ Error al canjear el código</h2>
            <p>{exc}</p>
        </body></html>
        """, status=500)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api/recomendar/', RecomendarView.as_view(), name='recomendar'),
    path('api/catalogo/', CatalogoView.as_view(), name='catalogo'),
    path('api/chat/', ChatView.as_view(), name='chat-gemini'),
    path('api/health/', health_check, name='health'),
    path('health/', health_check, name='health-root'),
    path('api/auth/mercadolibre/callback/', mercadolibre_callback, name='ml-callback'),
]

