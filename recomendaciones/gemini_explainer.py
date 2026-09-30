"""
Módulo de integración con Google Gemini API.

Genera explicaciones en lenguaje simple de por qué un equipo
fue recomendado, dado el tipo de uso del usuario.

Uso:
    from recomendaciones.gemini_explainer import generar_explicacion

    texto = generar_explicacion(equipo_dict, tipo_uso='gaming')
"""
import os
import logging

logger = logging.getLogger(__name__)


def generar_explicacion(equipo: dict, tipo_uso: str) -> str:
    """
    Usa Google Gemini para generar una explicación breve y amigable
    de por qué el equipo es adecuado para el tipo de uso indicado.

    Args:
        equipo: Dict con las características del equipo recomendado.
        tipo_uso: Perfil de uso del usuario (ej: 'gaming', 'oficina').

    Returns:
        Explicación en texto plano (1-2 oraciones). Si la API no está
        disponible, retorna un mensaje genérico.
    """
    api_key = os.environ.get('GEMINI_API_KEY', '').strip()

    if not api_key:
        logger.warning(
            "GEMINI_API_KEY no configurada. Retornando explicación genérica."
        )
        return _explicacion_generica(equipo, tipo_uso)

    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')

        prompt = _construir_prompt(equipo, tipo_uso)
        response = model.generate_content(prompt)
        return response.text.strip()

    except Exception as exc:
        logger.error("Error al llamar a Gemini API: %s", exc)
        return _explicacion_generica(equipo, tipo_uso)


def _construir_prompt(equipo: dict, tipo_uso: str) -> str:
    """Construye el prompt para Gemini."""
    return (
        f"Eres un experto en tecnología y hardware. Explica en máximo 2 oraciones breves, "
        f"en español claro y profesional, por qué el siguiente equipo es una excelente opción "
        f"de compra para uso de {tipo_uso}.\n\n"
        f"Equipo: {equipo.get('marca')} {equipo.get('modelo')}\n"
        f"Procesador: {equipo.get('procesador')}\n"
        f"RAM: {equipo.get('memoria_ram')} GB\n"
        f"Almacenamiento: {equipo.get('almacenamiento')}\n"
        f"Tarjeta gráfica: {equipo.get('tarjeta_grafica', 'Integrada')}\n"
        f"Precio: ${float(equipo.get('precio', 0)):,.2f} USD\n"
        f"Tienda: {equipo.get('tienda', 'Google Shopping')}\n\n"
        f"Responde solo con la explicación concisa destacando su valor para el tipo de uso, sin títulos ni viñetas."
    )


def _explicacion_generica(equipo: dict, tipo_uso: str) -> str:
    """Fallback cuando Gemini no está disponible."""
    ram = equipo.get('memoria_ram', 0)
    procesador = equipo.get('procesador', '')
    gpu = equipo.get('tarjeta_grafica', 'Integrada')
    precio = float(equipo.get('precio', 0))
    return (
        f"El {equipo.get('marca')} {equipo.get('modelo')} con {ram}GB de RAM, "
        f"procesador {procesador} y {gpu} es una sólida opción para {tipo_uso} "
        f"a ${precio:,.2f} USD, con excelente relación calidad-precio."
    )


def chat_gemini(mensaje: str, tipo_uso: str, tipo_equipo: str, equipos: list) -> str:
    """
    Función conversacional con Gemini AI.

    Recibe un mensaje libre del usuario y una lista de equipos como contexto,
    y retorna una respuesta fundamentada en el catálogo de Mercado Libre Perú.

    Args:
        mensaje: Pregunta o petición del usuario.
        tipo_uso: Perfil de uso (gaming, diseño, etc.)
        tipo_equipo: Tipo de equipo buscado.
        equipos: Lista de dicts con las especificaciones de los equipos disponibles.

    Returns:
        Respuesta conversacional en texto plano.
    """
    api_key = os.environ.get('GEMINI_API_KEY', '').strip()

    if not api_key:
        logger.warning("GEMINI_API_KEY no configurada. Retornando respuesta genérica de chat.")
        return _chat_generico(mensaje, equipos)

    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')

        # Construir contexto con los equipos disponibles
        catalogo_texto = _construir_contexto_catalogo(equipos)

        prompt = (
            f"Eres un asistente experto en hardware y tecnología especializado en laptops y PCs "
            f"de Mercado Libre Perú. Respondes en español de manera amigable, concisa y técnicamente precisa. "
            f"El usuario tiene perfil de uso '{tipo_uso}' y busca '{tipo_equipo}'.\n\n"
            f"CATÁLOGO DISPONIBLE EN MERCADO LIBRE PERÚ:\n{catalogo_texto}\n\n"
            f"PREGUNTA DEL USUARIO: {mensaje}\n\n"
            f"Responde directamente sobre los equipos del catálogo. "
            f"Si el usuario pide una descripción específica, da detalles técnicos y por qué es buena para su perfil. "
            f"Si el usuario da 'visto bueno' a un equipo, confirma que es una excelente elección y da el enlace de Mercado Libre. "
            f"Usa **negrita** para resaltar información importante. "
            f"Máximo 3-4 oraciones o puntos cortos."
        )

        response = model.generate_content(prompt)
        return response.text.strip()

    except Exception as exc:
        logger.error("Error en chat_gemini: %s", exc)
        return _chat_generico(mensaje, equipos)


def _construir_contexto_catalogo(equipos: list) -> str:
    """Construye un resumen textual del catálogo para el prompt de Gemini."""
    if not equipos:
        return "No hay equipos disponibles en el catálogo actual."

    lineas = []
    for i, eq in enumerate(equipos[:10], 1):  # Máx 10 para no exceder tokens
        lineas.append(
            f"{i}. {eq.get('marca', '')} {eq.get('modelo', '')} | "
            f"CPU: {eq.get('procesador', 'N/D')} | "
            f"RAM: {eq.get('memoria_ram', 'N/D')}GB | "
            f"Almac: {eq.get('almacenamiento', 'N/D')} | "
            f"GPU: {eq.get('tarjeta_grafica', 'Integrada')} | "
            f"Precio: S/. {float(eq.get('precio', 0)):,.0f}"
        )
    return '\n'.join(lineas)


def _chat_generico(mensaje: str, equipos: list) -> str:
    """Respuesta genérica cuando Gemini no está disponible."""
    if not equipos:
        return (
            "No tengo equipos en el catálogo para analizar en este momento. "
            "Por favor realiza primero una búsqueda en Mercado Libre."
        )

    mejor = equipos[0]
    return (
        f"Basándome en el catálogo de Mercado Libre Perú, el equipo más recomendado para tu consulta es "
        f"el **{mejor.get('marca')} {mejor.get('modelo')}** con {mejor.get('memoria_ram')}GB RAM, "
        f"{mejor.get('procesador')}, a S/. {float(mejor.get('precio', 0)):,.0f}. "
        f"Tiene un beneficio estimado del {mejor.get('porcentaje_beneficio', 80)}% para tu perfil."
    )
