"""
Comando personalizado de Django: vincular_mercadolibre

Permite autorizar la aplicación de Mercado Libre Perú mediante OAuth 2.0.
1. Muestra la URL de autorización para abrir en el navegador.
2. Recibe el código de autorización (o la URL de redirección completa).
3. Canjea el código por Access Token y Refresh Token.
4. Guarda automáticamente los tokens en el archivo .env.

Uso:
    python manage.py vincular_mercadolibre
    python manage.py vincular_mercadolibre --code TG-66f8...
    python manage.py vincular_mercadolibre --url-solo
"""
import sys
from django.core.management.base import BaseCommand, CommandError

from equipos.scraping.ml_auth import (
    generar_url_autorizacion,
    canjear_codigo_por_token,
    get_ml_credentials,
)

# Configurar salida segura en Windows
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass


class Command(BaseCommand):
    help = 'Vincula la aplicación de Mercado Libre mediante OAuth 2.0 y guarda los tokens en .env'

    def add_arguments(self, parser):
        parser.add_argument(
            '--code',
            type=str,
            default=None,
            help='Código de autorización o URL completa devuelta por Mercado Libre tras aprobar el acceso.',
        )
        parser.add_argument(
            '--url-solo',
            action='store_true',
            default=False,
            help='Solo genera y muestra la URL de autorización sin solicitar el código.',
        )
        parser.add_argument(
            '--redirect-uri',
            type=str,
            default=None,
            help='Sobrescribir la URL de redirección configurada.',
        )

    def handle(self, *args, **options):
        creds = get_ml_credentials()
        client_id = creds['client_id']
        redirect_uri = options.get('redirect_uri') or creds['redirect_uri']

        if not client_id:
            raise CommandError("No se encontró ML_CLIENT_ID en las variables de entorno o archivo .env.")

        # Generar URL de autorización
        auth_url = generar_url_autorizacion(client_id=client_id, redirect_uri=redirect_uri)

        self.stdout.write("\n" + "=" * 70)
        self.stdout.write(self.style.SUCCESS("  VINCULACIÓN OAUTH 2.0 CON MERCADO LIBRE PERÚ (MPE)"))
        self.stdout.write("=" * 70)
        self.stdout.write(f"\n1. Copia y abre la siguiente URL en tu navegador:\n")
        self.stdout.write(self.style.WARNING(f"   {auth_url}\n"))
        self.stdout.write(f"   (Redirect URI configurada: {redirect_uri})\n")
        self.stdout.write("2. Inicia sesión en Mercado Libre y presiona 'Permitir / Continuar'.")
        self.stdout.write("3. El navegador te redirigirá a una dirección como:")
        self.stdout.write(self.style.NOTICE(f"   {redirect_uri}/?code=TG-66f8..."))
        self.stdout.write("-" * 70)

        if options.get('url_solo'):
            return

        code_input = options.get('code')

        # Si no se pasó por parámetro --code, pedirlo interactivamente
        if not code_input:
            self.stdout.write("\nPega aquí el código recibido (o la URL completa de redirección):")
            try:
                code_input = input("> ").strip()
            except (KeyboardInterrupt, EOFError):
                self.stdout.write("\nOperación cancelada por el usuario.")
                return

        if not code_input:
            raise CommandError("No se ingresó ningún código.")

        self.stdout.write("\nCanjeando código por tokens de acceso en Mercado Libre...")

        try:
            tokens = canjear_codigo_por_token(
                codigo=code_input,
                client_id=client_id,
                client_secret=creds['client_secret'],
                redirect_uri=redirect_uri,
            )

            access_token = tokens.get('access_token', '')
            user_id = tokens.get('user_id', '')
            expires_in = tokens.get('expires_in', 21600)

            self.stdout.write("\n" + "=" * 70)
            self.stdout.write(self.style.SUCCESS("✅ ¡AUTENTICACIÓN CON MERCADO LIBRE EXITOSA!"))
            self.stdout.write("=" * 70)
            self.stdout.write(f"• Usuario / Vendedor ID: {user_id}")
            self.stdout.write(f"• Duración del token:    {expires_in // 3600} horas ({expires_in} segundos)")
            self.stdout.write(f"• Access Token:          {access_token[:15]}...{access_token[-5:]}")
            self.stdout.write(self.style.SUCCESS("• Tokens guardados en:   backend/.env"))
            self.stdout.write("\n🚀 Ahora puedes ejecutar la sincronización de productos reales con:")
            self.stdout.write(self.style.WARNING("   python manage.py actualizar_precios\n"))

        except Exception as exc:
            self.stdout.write(self.style.ERROR(f"\n❌ Error al canjear código: {exc}"))
            raise CommandError(str(exc))
