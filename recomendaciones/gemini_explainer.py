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
        f"en español claro y profesional, por qué el siguiente equipo disponible en Mercado Libre Perú "
        f"es una excelente opción de compra para uso de {tipo_uso}.\n\n"
        f"Equipo: {equipo.get('marca')} {equipo.get('modelo')}\n"
        f"Procesador: {equipo.get('procesador')}\n"
        f"RAM: {equipo.get('memoria_ram')} GB\n"
        f"Almacenamiento: {equipo.get('almacenamiento')}\n"
        f"Tarjeta gráfica: {equipo.get('tarjeta_grafica', 'Integrada')}\n"
        f"Precio: S/. {float(equipo.get('precio', 0)):,.2f} (Soles Peruanos)\n"
        f"Plataforma: Mercado Libre Perú\n\n"
        f"Responde solo con la explicación concisa, destacando su valor en Mercado Libre, sin títulos ni viñetas."
    )


def _explicacion_generica(equipo: dict, tipo_uso: str) -> str:
    """Fallback cuando Gemini no está disponible."""
    ram = equipo.get('memoria_ram', 0)
    procesador = equipo.get('procesador', '')
    return (
        f"El {equipo.get('marca')} {equipo.get('modelo')} con {ram}GB de RAM "
        f"y procesador {procesador} es una excelente opción en Mercado Libre Perú para {tipo_uso}, "
        f"equilibrando rendimiento, disponibilidad y precio dentro de tu presupuesto."
    )
