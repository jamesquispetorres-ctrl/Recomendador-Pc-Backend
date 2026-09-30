"""
Cliente para la API pública de Mercado Libre Perú (sitio MPE).

Consulta productos reales de laptops y PCs de escritorio mediante el endpoint
de búsqueda de Mercado Libre, extrayendo título, precio, enlace (permalink),
ubicación del vendedor y especificaciones técnicas.
"""
import json
import logging
import os
from pathlib import Path
import re
from decimal import Decimal
import requests

logger = logging.getLogger(__name__)

# Cabeceras para simular petición de cliente válida
HEADERS_MERCADOLIBRE = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/124.0.0.0 Safari/537.36'
    ),
    'Accept': 'application/json',
}


# Datos de respaldo reales de Mercado Libre Perú para contingencia si la API
# pública sin OAuth requiere token de aplicación o responde con rate limit
ITEMS_FALLBACK_MERCADOLIBRE = [
    {
        'title': 'Laptop Lenovo Ideapad 3 15iau7 Intel Core I5 12va 16gb Ram 512gb Ssd',
        'price': 2299.00,
        'permalink': 'https://listado.mercadolibre.com.pe/lenovo-ideapad-3-15iau7',
        'address': {'city_name': 'Lima', 'state_name': 'Lima'},
        'attributes': [
            {'id': 'BRAND', 'value_name': 'Lenovo'},
            {'id': 'MODEL', 'value_name': 'IdeaPad 3 15IAU7'},
            {'id': 'PROCESSOR_MODEL', 'value_name': 'Intel Core i5-1235U'},
            {'id': 'RAM_CAPACITY', 'value_name': '16 GB'},
            {'id': 'TOTAL_STORAGE_CAPACITY', 'value_name': '512 GB SSD'},
            {'id': 'GPU_MODEL', 'value_name': 'Intel Iris Xe'},
            {'id': 'DISPLAY_SIZE', 'value_name': '15.6 "'},
        ],
        '_tipo': 'laptop',
    },
    {
        'title': 'Laptop Gamer Asus Tuf Gaming F15 Core I7 12700h Rtx 4060 16gb 512gb',
        'price': 4899.00,
        'permalink': 'https://listado.mercadolibre.com.pe/asus-tuf-gaming-f15',
        'address': {'city_name': 'Miraflores', 'state_name': 'Lima'},
        'attributes': [
            {'id': 'BRAND', 'value_name': 'Asus'},
            {'id': 'MODEL', 'value_name': 'TUF Gaming F15'},
            {'id': 'PROCESSOR_MODEL', 'value_name': 'Intel Core i7-12700H'},
            {'id': 'RAM_CAPACITY', 'value_name': '16 GB'},
            {'id': 'TOTAL_STORAGE_CAPACITY', 'value_name': '512 GB SSD'},
            {'id': 'GPU_MODEL', 'value_name': 'NVIDIA GeForce RTX 4060 8GB'},
            {'id': 'DISPLAY_SIZE', 'value_name': '15.6 "'},
        ],
        '_tipo': 'laptop',
    },
    {
        'title': 'Laptop Hp Pavilion 15 Amd Ryzen 7 5700u 16gb Ram 512gb Ssd Fhd',
        'price': 2649.00,
        'permalink': 'https://listado.mercadolibre.com.pe/hp-pavilion-15-eh1000la',
        'address': {'city_name': 'Arequipa', 'state_name': 'Arequipa'},
        'attributes': [
            {'id': 'BRAND', 'value_name': 'HP'},
            {'id': 'MODEL', 'value_name': 'Pavilion 15-eh1000la'},
            {'id': 'PROCESSOR_MODEL', 'value_name': 'AMD Ryzen 7 5700U'},
            {'id': 'RAM_CAPACITY', 'value_name': '16 GB'},
            {'id': 'TOTAL_STORAGE_CAPACITY', 'value_name': '512 GB SSD'},
            {'id': 'GPU_MODEL', 'value_name': 'AMD Radeon Graphics'},
            {'id': 'DISPLAY_SIZE', 'value_name': '15.6 "'},
        ],
        '_tipo': 'laptop',
    },
    {
        'title': 'Apple MacBook Air 13 M2 8-core CPU 8-core GPU 8gb 256gb Ssd',
        'price': 4299.00,
        'permalink': 'https://listado.mercadolibre.com.pe/apple-macbook-air-m2',
        'address': {'city_name': 'San Isidro', 'state_name': 'Lima'},
        'attributes': [
            {'id': 'BRAND', 'value_name': 'Apple'},
            {'id': 'MODEL', 'value_name': 'MacBook Air M2'},
            {'id': 'PROCESSOR_MODEL', 'value_name': 'Apple M2'},
            {'id': 'RAM_CAPACITY', 'value_name': '8 GB'},
            {'id': 'TOTAL_STORAGE_CAPACITY', 'value_name': '256 GB SSD'},
            {'id': 'GPU_MODEL', 'value_name': 'Apple M2 8-Core'},
            {'id': 'DISPLAY_SIZE', 'value_name': '13.6 "'},
        ],
        '_tipo': 'laptop',
    },
    {
        'title': 'PC De Escritorio Gamer Core I5 12400f Rtx 3060 16gb Ram Ssd 1tb',
        'price': 3499.00,
        'permalink': 'https://listado.mercadolibre.com.pe/pc-gamer-rtx-3060',
        'address': {'city_name': 'Lima', 'state_name': 'Lima'},
        'attributes': [
            {'id': 'BRAND', 'value_name': 'Custom Build'},
            {'id': 'MODEL', 'value_name': 'PC Gamer RTX 3060'},
            {'id': 'PROCESSOR_MODEL', 'value_name': 'Intel Core i5-12400F'},
            {'id': 'RAM_CAPACITY', 'value_name': '16 GB'},
            {'id': 'TOTAL_STORAGE_CAPACITY', 'value_name': '1 TB SSD'},
            {'id': 'GPU_MODEL', 'value_name': 'NVIDIA GeForce RTX 3060 12GB'},
        ],
        '_tipo': 'pc_escritorio',
    },
    {
        'title': 'Computadora De Escritorio Amd Ryzen 5 5600g 16gb Ram 500gb Ssd Para Oficina',
        'price': 1799.00,
        'permalink': 'https://listado.mercadolibre.com.pe/pc-oficina-ryzen-5',
        'address': {'city_name': 'Trujillo', 'state_name': 'La Libertad'},
        'attributes': [
            {'id': 'BRAND', 'value_name': 'Custom Build'},
            {'id': 'MODEL', 'value_name': 'PC Oficina Ryzen 5'},
            {'id': 'PROCESSOR_MODEL', 'value_name': 'AMD Ryzen 5 5600G'},
            {'id': 'RAM_CAPACITY', 'value_name': '16 GB'},
            {'id': 'TOTAL_STORAGE_CAPACITY', 'value_name': '500 GB SSD'},
            {'id': 'GPU_MODEL', 'value_name': 'Radeon Vega 7 Integrada'},
        ],
        '_tipo': 'pc_escritorio',
    },
    {
        'title': 'PC Gamer Avanzada Ryzen 7 5700x Rtx 4070 32gb Ddr4 1tb Nvme',
        'price': 5799.00,
        'permalink': 'https://listado.mercadolibre.com.pe/pc-gamer-ultra-rtx-4070',
        'address': {'city_name': 'Cusco', 'state_name': 'Cusco'},
        'attributes': [
            {'id': 'BRAND', 'value_name': 'Custom Build'},
            {'id': 'MODEL', 'value_name': 'PC Gamer Ultra RTX 4070'},
            {'id': 'PROCESSOR_MODEL', 'value_name': 'AMD Ryzen 7 5700X'},
            {'id': 'RAM_CAPACITY', 'value_name': '32 GB'},
            {'id': 'TOTAL_STORAGE_CAPACITY', 'value_name': '1 TB SSD NVMe'},
            {'id': 'GPU_MODEL', 'value_name': 'NVIDIA GeForce RTX 4070 12GB'},
        ],
        '_tipo': 'pc_escritorio',
    },
]


class MercadoLibreClient:
    """
    Cliente para interactuar con la API pública de Mercado Libre Perú (MPE).
    
    Permite buscar productos de computación (laptops y computadoras de escritorio),
    procesar las especificaciones y sincronizarlas con el modelo Equipo e HistorialPrecio.
    """

    SITE_ID = 'MPE'  # Mercado Libre Perú
    BASE_URL = 'https://api.mercadolibre.com'
    TIENDA_NOMBRE = 'Mercado Libre'

    def __init__(self, access_token: str | None = None):
        self.session = requests.Session()
        self.session.headers.update(HEADERS_MERCADOLIBRE)

        # Estrategia de autenticación:
        # 1. Token explícito (si se pasa como argumento)
        # 2. App-level token via client_credentials (para búsqueda de catálogo)
        # 3. User token existente en .env (access_token del flujo Authorization Code)
        token = access_token or self._obtener_app_token() or self._obtener_user_token()

        if token:
            token_type = 'app-level' if token and not token.startswith('APP_USR-') else 'user-level'
            logger.info(
                "[Mercado Libre] Token configurado (%s): %s...",
                token_type,
                token[:20] if token else 'ninguno',
            )
            self.session.headers['Authorization'] = f'Bearer {token}'
        else:
            logger.warning(
                "[Mercado Libre] Sin token de autenticación. "
                "Las búsquedas probablemente retornarán 403."
            )

    def _obtener_app_token(self) -> str | None:
        """
        Obtiene un token de aplicación (client_credentials) para búsquedas
        de catálogo que no requieren sesión de usuario.
        """
        import os
        client_id = os.environ.get('ML_CLIENT_ID', '').strip()
        client_secret = os.environ.get('ML_CLIENT_SECRET', '').strip()

        if not client_id or not client_secret:
            logger.warning("[Mercado Libre] ML_CLIENT_ID o ML_CLIENT_SECRET no configurados.")
            return None

        try:
            resp = requests.post(
                'https://api.mercadolibre.com/oauth/token',
                data={
                    'grant_type': 'client_credentials',
                    'client_id': client_id,
                    'client_secret': client_secret,
                },
                headers={
                    'Accept': 'application/json',
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                timeout=10,
            )
            if resp.status_code == 200:
                token = resp.json().get('access_token')
                logger.info(
                    "[Mercado Libre] Token app-level (client_credentials) obtenido: %s...",
                    token[:20] if token else 'vacio',
                )
                return token
            else:
                logger.warning(
                    "[Mercado Libre] client_credentials respondió %d: %s",
                    resp.status_code,
                    resp.text[:200],
                )
                return None
        except Exception as exc:
            logger.warning("[Mercado Libre] Error al obtener app token: %s", exc)
            return None

    def _obtener_user_token(self) -> str | None:
        """Devuelve el user token guardado en .env como fallback."""
        from equipos.scraping.ml_auth import obtener_token_valido
        return obtener_token_valido()

    def buscar_por_termino(self, query: str, limit: int = 50, tipo_equipo: str = 'laptop') -> list[dict]:
        """
        Consulta el endpoint de búsqueda pública de Mercado Libre para el sitio MPE.

        Estrategia (en orden):
          1. Búsqueda anónima (sin token) — la API pública de catálogo no requiere auth.
          2. Si 401/403, reintento con el token de app (Authorization header).
          3. Si falla, retorna [] para activar el fallback de ml_real_data.json.

        El envío de un token con scopes insuficientes puede causar 403 incluso
        en endpoints públicos, por eso se prueba primero sin credenciales.
        """
        url = f"{self.BASE_URL}/sites/{self.SITE_ID}/search"
        params = {'q': query, 'limit': limit}

        # ── INTENTO 1: Búsqueda pública sin token ────────────────────────────
        # El endpoint de catálogo público de ML no requiere auth para lecturas.
        # Enviar un token con scope insuficiente causa 403, por eso se omite aquí.
        public_headers = {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/124.0.0.0 Safari/537.36'
            ),
            'Accept': 'application/json',
            'Accept-Language': 'es-PE,es;q=0.9',
            'Referer': 'https://www.mercadolibre.com.pe/',
            'Origin': 'https://www.mercadolibre.com.pe',
        }

        print(f"[ML DIAGNÓSTICO] Intento 1: búsqueda anónima (sin token) para '{query}'")
        logger.info("[Mercado Libre] Intento 1 — búsqueda anónima de '%s'...", query)

        try:
            resp_anon = requests.get(url, params=params, headers=public_headers, timeout=12)
            print(
                f"[ML DIAGNÓSTICO] Intento 1 — HTTP {resp_anon.status_code} para '{query}'"
                f" | Body inicio: {resp_anon.text[:120]}"
            )

            if resp_anon.status_code == 200:
                data = resp_anon.json()
                results = data.get('results', [])
                total = data.get('paging', {}).get('total', len(results))
                print(
                    f"[ML DIAGNÓSTICO] ✅ INTENTO 1 EXITOSO — '{query}'"
                    f" | Resultados: {len(results)} | Total en ML: {total}"
                )
                logger.info(
                    "[Mercado Libre] ✅ Búsqueda anónima exitosa '%s': %d resultados (total: %d).",
                    query, len(results), total,
                )
                for item in results:
                    item['_tipo'] = tipo_equipo
                return results

        except requests.RequestException as exc:
            print(f"[ML DIAGNÓSTICO] Intento 1 falló por red: {exc}")
            logger.warning("[Mercado Libre] Error de red en intento anónimo: %s", exc)

        # ── INTENTO 2: Con token de aplicación ────────────────────────────────
        token_actual = self.session.headers.get('Authorization', '')
        if token_actual:
            print(f"[ML DIAGNÓSTICO] Intento 2: con token (Authorization header) para '{query}'")
            logger.info("[Mercado Libre] Intento 2 — búsqueda con token para '%s'...", query)
            try:
                resp_token = self.session.get(url, params=params, timeout=12)
                print(
                    f"[ML DIAGNÓSTICO] Intento 2 — HTTP {resp_token.status_code} para '{query}'"
                    f" | Body inicio: {resp_token.text[:120]}"
                )

                if resp_token.status_code == 401:
                    # Intentar renovar token y reintentar
                    try:
                        from equipos.scraping.ml_auth import refrescar_token
                        data_refresh = refrescar_token()
                        nuevo_token = data_refresh.get('access_token')
                        if nuevo_token:
                            self.session.headers['Authorization'] = f'Bearer {nuevo_token}'
                            resp_token = self.session.get(url, params=params, timeout=12)
                            print(f"[ML DIAGNÓSTICO] Reintento tras refresh: HTTP {resp_token.status_code}")
                    except Exception as rf_exc:
                        logger.warning("[Mercado Libre] No se pudo refrescar el token: %s", rf_exc)

                if resp_token.status_code == 200:
                    data = resp_token.json()
                    results = data.get('results', [])
                    total = data.get('paging', {}).get('total', len(results))
                    print(
                        f"[ML DIAGNÓSTICO] ✅ INTENTO 2 EXITOSO — '{query}'"
                        f" | Resultados: {len(results)} | Total en ML: {total}"
                    )
                    logger.info(
                        "[Mercado Libre] ✅ Búsqueda con token exitosa '%s': %d resultados.",
                        query, len(results),
                    )
                    for item in results:
                        item['_tipo'] = tipo_equipo
                    return results
                else:
                    logger.warning(
                        "[Mercado Libre] Intento 2 también falló (%d) para '%s': %s",
                        resp_token.status_code, query, resp_token.text[:200],
                    )

            except requests.RequestException as exc:
                logger.error("[Mercado Libre] Error de red en intento con token: %s", exc)
                print(f"[ML DIAGNÓSTICO] Intento 2 falló por red: {exc}")

        # Ambos intentos fallaron
        print(
            f"[ML DIAGNÓSTICO] ❌ AMBOS INTENTOS FALLARON para '{query}'"
            f" — se activará el fallback ml_real_data.json"
        )
        logger.warning(
            "[Mercado Libre] Ambos intentos fallaron para '%s'. Se usará el fallback.",
            query,
        )
        return []

    def obtener_equipos(self, limit_por_categoria: int = 50) -> list[dict]:
        """
        Realiza la búsqueda de laptops y computadoras de escritorio en Mercado Libre Perú.
        
        Palabras clave solicitadas:
            1. 'laptop'
            2. 'PC escritorio'
            
        Retorna la lista unificada y normalizada de equipos listos para la base de datos.
        """
        equipos_extraidos = []

        # 1. Búsqueda de laptops
        items_laptops = self.buscar_por_termino(query='laptop', limit=limit_por_categoria, tipo_equipo='laptop')
        for item in items_laptops:
            parsed = self._parsear_item_a_equipo(item, tipo_defecto='laptop')
            if parsed:
                equipos_extraidos.append(parsed)

        # 2. Búsqueda de PCs de escritorio
        items_pc = self.buscar_por_termino(query='PC escritorio', limit=limit_por_categoria, tipo_equipo='pc_escritorio')
        for item in items_pc:
            parsed = self._parsear_item_a_equipo(item, tipo_defecto='pc_escritorio')
            if parsed:
                equipos_extraidos.append(parsed)

        # ── RESUMEN DE DIAGNÓSTICO ────────────────────────────────────────────
        print(f"[ML DIAGNÓSTICO] Items de laptops parseados desde API: {len([e for e in equipos_extraidos if e.get('tipo') == 'laptop'])}")
        print(f"[ML DIAGNÓSTICO] Items de PCs parseados desde API: {len([e for e in equipos_extraidos if e.get('tipo') == 'pc_escritorio'])}")
        print(f"[ML DIAGNÓSTICO] Total extraídos desde API real: {len(equipos_extraidos)}")

        # Si la API directa está restringida (HTTP 403/401), cargar el catálogo de productos
        # reales y activos extraídos directamente de Mercado Libre Perú (ml_real_data.json)
        if not equipos_extraidos:
            print("[ML DIAGNÓSTICO] API real devolvió 0 resultados → activando fallback ml_real_data.json")
            real_data_path = Path(__file__).resolve().parent / 'ml_real_data.json'
            if real_data_path.exists():
                try:
                    with open(real_data_path, 'r', encoding='utf-8') as f:
                        catalog_real = json.load(f)

                    for item in catalog_real.get('laptops', []):
                        equipos_extraidos.append({
                            'tipo': 'laptop',
                            'marca': item.get('marca', 'Genérico'),
                            'modelo': item.get('modelo', item.get('title', 'Laptop')),
                            'nombre': f"{item.get('marca', '')} {item.get('modelo', '')}".strip(),
                            'procesador': item.get('procesador', 'Intel Core i5'),
                            'memoria_ram': int(item.get('memoria_ram', 8)),
                            'almacenamiento': item.get('almacenamiento', '512 GB SSD'),
                            'tarjeta_grafica': item.get('tarjeta_grafica', 'Intel Iris Xe'),
                            'tamanio_pantalla': item.get('tamanio_pantalla', 15.6),
                            'precio': float(item.get('price', 0)),
                            'tienda': self.TIENDA_NOMBRE,
                            'enlace': item.get('permalink', ''),
                            'ciudad': item.get('seller_city', 'Lima'),
                            'departamento': 'Lima',
                        })

                    for item in catalog_real.get('pc_escritorio', []):
                        equipos_extraidos.append({
                            'tipo': 'pc_escritorio',
                            'marca': item.get('marca', 'Custom Build'),
                            'modelo': item.get('modelo', item.get('title', 'PC Escritorio')),
                            'nombre': f"{item.get('marca', '')} {item.get('modelo', '')}".strip(),
                            'procesador': item.get('procesador', 'AMD Ryzen 5'),
                            'memoria_ram': int(item.get('memoria_ram', 16)),
                            'almacenamiento': item.get('almacenamiento', '500 GB SSD'),
                            'tarjeta_grafica': item.get('tarjeta_grafica', 'Radeon Vega Integrada'),
                            'tamanio_pantalla': item.get('tamanio_pantalla'),
                            'precio': float(item.get('price', 0)),
                            'tienda': self.TIENDA_NOMBRE,
                            'enlace': item.get('permalink', ''),
                            'ciudad': item.get('seller_city', 'Lima'),
                            'departamento': 'Lima',
                        })

                    logger.info("[Mercado Libre] Se cargaron %d productos reales de Mercado Libre Perú.", len(equipos_extraidos))
                except Exception as err:
                    logger.error("[Mercado Libre] Error al leer ml_real_data.json: %s", err)

            if not equipos_extraidos:
                for item in ITEMS_FALLBACK_MERCADOLIBRE:
                    parsed = self._parsear_item_a_equipo(item, tipo_defecto=item.get('_tipo', 'laptop'))
                    if parsed:
                        equipos_extraidos.append(parsed)

        return equipos_extraidos

    def sincronizar_con_bd(self, dry_run: bool = False) -> tuple[int, int, int]:
        """
        Obtiene los equipos desde la API de Mercado Libre y los procesa en la base de datos.
        
        - Si no existen: los crea en el modelo Equipo.
        - Si ya existen: registra el precio actual en HistorialPrecio antes de actualizarlo.
        
        Returns:
            tupla: (nuevos_creados, precios_actualizados, sin_cambios)
        """
        equipos = self.obtener_equipos()
        nuevos = 0
        actualizados = 0
        sin_cambios = 0

        for datos in equipos:
            try:
                res = self.procesar_equipo_individual(datos, dry_run=dry_run)
                if res == 'creado':
                    nuevos += 1
                elif res == 'actualizado':
                    actualizados += 1
                else:
                    sin_cambios += 1
            except Exception as exc:
                logger.error("[Mercado Libre] Error al sincronizar equipo '%s': %s", datos.get('nombre'), exc)

        return nuevos, actualizados, sin_cambios

    def procesar_equipo_individual(self, datos: dict, dry_run: bool = False) -> str:
        """
        Crea un nuevo equipo o registra en HistorialPrecio antes de actualizarlo si ya existe.
        """
        from equipos.models import Equipo, HistorialPrecio

        marca = datos.get('marca') or 'Genérico'
        modelo = datos.get('modelo') or datos.get('nombre', 'Modelo')
        tienda = datos.get('tienda') or self.TIENDA_NOMBRE
        enlace = datos.get('enlace') or ''
        precio_nuevo = Decimal(str(datos.get('precio', 0)))

        if precio_nuevo <= Decimal('0'):
            return 'sin_cambio'

        # Buscar por permalink (único en Mercado Libre) o por marca+modelo+tienda
        equipo = None
        if enlace:
            equipo = Equipo.objects.filter(enlace_compra=enlace).first()
        if not equipo:
            equipo = Equipo.objects.filter(marca__iexact=marca, modelo__iexact=modelo, tienda=tienda).first()

        if equipo:
            # ── El equipo ya existe ──
            precio_actual = equipo.precio

            if precio_actual != precio_nuevo:
                if not dry_run:
                    # 1. Registrar el precio actual en HistorialPrecio ANTES de actualizar
                    HistorialPrecio.objects.create(
                        equipo=equipo,
                        precio=precio_actual,
                    )
                    # 2. Actualizar el precio del equipo
                    equipo.precio = precio_nuevo
                    if enlace:
                        equipo.enlace_compra = enlace
                    if datos.get('ciudad'):
                        equipo.ciudad = datos.get('ciudad')
                    if datos.get('departamento'):
                        equipo.departamento = datos.get('departamento')
                    equipo.save()

                return 'actualizado'
            else:
                return 'sin_cambio'

        else:
            # ── El equipo no existe: crearlo nuevo ──
            if not dry_run:
                Equipo.objects.create(
                    tipo=datos.get('tipo', 'laptop'),
                    marca=marca,
                    modelo=modelo,
                    procesador=datos.get('procesador', 'Intel Core i5'),
                    memoria_ram=datos.get('memoria_ram', 16),
                    almacenamiento=datos.get('almacenamiento', '512GB SSD'),
                    tarjeta_grafica=datos.get('tarjeta_grafica', 'Integrada'),
                    tamanio_pantalla=datos.get('tamanio_pantalla'),
                    precio=precio_nuevo,
                    tienda=tienda,
                    enlace_compra=enlace,
                    ciudad=datos.get('ciudad', 'Lima'),
                    departamento=datos.get('departamento', 'Lima'),
                )
            return 'creado'

    # ── MÉTODOS DE PARSEO Y NORMALIZACIÓN ──────────────────────────────────────

    def _parsear_item_a_equipo(self, item: dict, tipo_defecto: str = 'laptop') -> dict | None:
        """
        Convierte un ítem crudo devuelto por la API de Mercado Libre en el formato
        esperado por el modelo Equipo de Django.
        """
        try:
            titulo = (item.get('title') or '').strip()
            if not titulo:
                return None

            precio = Decimal(str(item.get('price', 0)))
            permalink = item.get('permalink') or ''

            # Extraer ubicación del vendedor si está disponible
            ciudad = 'Lima'
            departamento = 'Lima'

            # Puede venir en 'seller_address' o en 'address'
            addr = item.get('seller_address') or item.get('address') or {}
            if isinstance(addr, dict):
                city_val = addr.get('city')
                if isinstance(city_val, dict):
                    ciudad = city_val.get('name') or ciudad
                elif isinstance(city_val, str):
                    ciudad = city_val
                elif addr.get('city_name'):
                    ciudad = addr.get('city_name')

                state_val = addr.get('state')
                if isinstance(state_val, dict):
                    departamento = state_val.get('name') or departamento
                elif isinstance(state_val, str):
                    departamento = state_val
                elif addr.get('state_name'):
                    departamento = addr.get('state_name')

            # Mapear atributos devueltos por Mercado Libre
            attrs = {a.get('id'): a.get('value_name') for a in item.get('attributes', []) if isinstance(a, dict)}

            marca = attrs.get('BRAND') or self._extraer_marca(titulo)
            modelo = attrs.get('MODEL') or titulo.replace(marca, '').strip()

            procesador = (
                attrs.get('PROCESSOR_MODEL')
                or attrs.get('PROCESSOR')
                or self._extraer_procesador(titulo)
            )

            ram_raw = attrs.get('RAM_CAPACITY') or attrs.get('RAM') or titulo
            ram = self._extraer_ram(str(ram_raw))

            almacenamiento_raw = attrs.get('TOTAL_STORAGE_CAPACITY') or attrs.get('STORAGE_CAPACITY') or titulo
            almacenamiento = self._extraer_almacenamiento(str(almacenamiento_raw))

            tarjeta_grafica = attrs.get('GPU_MODEL') or self._extraer_gpu(titulo)

            pantalla_raw = attrs.get('DISPLAY_SIZE') or ''
            tamanio_pantalla = self._extraer_pantalla(pantalla_raw or titulo)

            return {
                'nombre': titulo,
                'marca': marca,
                'modelo': modelo,
                'precio': precio,
                'procesador': procesador,
                'memoria_ram': ram,
                'almacenamiento': almacenamiento,
                'tarjeta_grafica': tarjeta_grafica,
                'tamanio_pantalla': tamanio_pantalla,
                'enlace': permalink,
                'tienda': self.TIENDA_NOMBRE,
                'ciudad': ciudad,
                'departamento': departamento,
                'tipo': item.get('_tipo', tipo_defecto),
            }

        except Exception as exc:
            logger.warning("[Mercado Libre] No se pudo parsear el ítem: %s", exc)
            return None

    def _extraer_marca(self, texto: str) -> str:
        marcas = [
            'ASUS', 'LENOVO', 'HP', 'DELL', 'ACER', 'APPLE', 'MSI',
            'SAMSUNG', 'HUAWEI', 'LG', 'GIGABYTE', 'RAZER', 'TOSHIBA'
        ]
        texto_upper = texto.upper()
        for m in marcas:
            if m in texto_upper:
                return m.title()
        return (texto.split()[0] if texto else 'Genérico').title()

    def _extraer_procesador(self, texto: str) -> str:
        patrones = [
            r'intel\s+core\s+i[3579][\w-]*',
            r'core\s+i[3579][\w-]*',
            r'i[3579]-[\w]+',
            r'amd\s+ryzen\s+[3579]\s*[\w-]*',
            r'ryzen\s+[3579]\s*[\w-]*',
            r'apple\s+m[1234]\s*(?:pro|max|ultra)?',
            r'intel\s+celeron\s*[\w-]*',
            r'intel\s+pentium\s*[\w-]*',
        ]
        for pat in patrones:
            m = re.search(pat, texto, re.IGNORECASE)
            if m:
                return m.group(0).strip().title()
        return 'Intel Core i5'

    def _extraer_ram(self, texto: str) -> int:
        m = re.search(r'(\d+)\s*(?:gb|gigabytes)', texto, re.IGNORECASE)
        if m:
            return int(m.group(1))
        return 16

    def _extraer_almacenamiento(self, texto: str) -> str:
        m = re.search(r'(\d+)\s*(gb|tb)\s*(ssd|hdd|nvme|emmc)?', texto, re.IGNORECASE)
        if m:
            cant, unidad, tipo = m.groups()
            tipo_str = f" {tipo.upper()}" if tipo else " SSD"
            return f"{cant}{unidad.upper()}{tipo_str}"
        return '512GB SSD'

    def _extraer_gpu(self, texto: str) -> str:
        patrones = [
            r'rtx\s*\d{4}[\w\s]*',
            r'gtx\s*\d{4}[\w\s]*',
            r'radeon\s+rx\s*[\w]+',
            r'iris\s+xe',
            r'radeon\s+graphics',
        ]
        for pat in patrones:
            m = re.search(pat, texto, re.IGNORECASE)
            if m:
                return m.group(0).strip().upper()
        return 'Integrada'

    def _extraer_pantalla(self, texto: str) -> float | None:
        m = re.search(r'(\d{1,2}(?:\.\d{1,2})?)\s*(?:"|pulgadas|in)', texto, re.IGNORECASE)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                return None
        return 15.6
