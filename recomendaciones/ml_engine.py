"""
Motor de recomendaciones usando scikit-learn.

Función principal:
    recomendar(presupuesto, tipo_uso, tipo_equipo, ubicacion) -> list[dict]

Algoritmo:
    1. Filtra equipos por presupuesto y tipo_equipo
    2. Filtra opcionalmente por ubicación (ciudad/departamento)
    3. Construye un texto de características por equipo
    4. Vectoriza con TF-IDF y calcula similitud coseno vs el tipo_uso
    5. Retorna top-10 ordenados por score de afinidad
"""
import logging
from decimal import Decimal
from typing import Literal

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

# ── Mapeo de tipos de uso a palabras clave ────────────────────────────────────
PERFILES_USO = {
    'gaming': (
        'gaming juegos tarjeta gráfica GPU dedicada RTX GTX RX rendimiento '
        'alto fps refresh rate pantalla 144hz procesador potente RAM 16GB 32GB '
        'refrigeración térmica SSD rápido'
    ),
    'diseño': (
        'diseño gráfico edición video color pantalla calibrada IPS OLED '
        'resolución alta RAM 16GB 32GB procesador rápido GPU dedicada '
        'almacenamiento SSD creativo Adobe Photoshop Premiere'
    ),
    'oficina': (
        'oficina trabajo productividad Word Excel PowerPoint ligero batería '
        'larga duración portátil empresarial administración contabilidad '
        'económico precio bajo procesador eficiente'
    ),
    'estudiante': (
        'estudiante universidad portátil ligero económico batería buena '
        'tareas trabajo remoto videoconferencia Zoom Teams duradero '
        'procesador básico almacenamiento suficiente'
    ),
    'programacion': (
        'programación desarrollo software IDE compilar múltiples monitores '
        'RAM 16GB 32GB procesador rápido SSD teclas cómodas pantalla grande '
        'Linux Ubuntu Docker virtualización'
    ),
    'multimedia': (
        'multimedia entretenimiento streaming Netflix YouTube pantalla grande '
        'sonido altavoces resolución full HD 4K gráficos integrados batería '
        'cámara web micrófono'
    ),
}


def _construir_texto_equipo(equipo) -> str:
    """
    Construye una cadena de texto con las características del equipo
    para ser vectorizada por TF-IDF.
    """
    partes = [
        equipo.marca,
        equipo.modelo,
        equipo.procesador,
        f"{equipo.memoria_ram}GB RAM",
        equipo.almacenamiento,
        equipo.tarjeta_grafica or '',
        equipo.tipo,
        equipo.tienda,
        equipo.ciudad,
        equipo.departamento,
        f"${float(equipo.precio):,.0f}",
    ]
    if equipo.tamanio_pantalla:
        partes.append(f"{equipo.tamanio_pantalla} pulgadas")
    return ' '.join(str(p) for p in partes if p)


def recomendar(
    presupuesto: float,
    tipo_uso: str,
    tipo_equipo: Literal['laptop', 'pc_escritorio', 'ambos'] = 'ambos',
    ubicacion: dict | None = None,
    top_n: int = 10,
) -> list[dict]:
    """
    Recomienda equipos basándose en presupuesto, tipo de uso y ubicación.

    Args:
        presupuesto: Precio máximo en COP.
        tipo_uso: Perfil de uso ('gaming', 'diseño', 'oficina', 'estudiante',
                                  'programacion', 'multimedia').
        tipo_equipo: 'laptop', 'pc_escritorio' o 'ambos'.
        ubicacion: dict con claves opcionales 'ciudad' y 'departamento'.
        top_n: Número máximo de resultados a retornar.

    Returns:
        Lista de dicts con datos del equipo + campo 'score' de afinidad.
    """
    # Importación diferida para evitar problemas de importación circular en Django
    from equipos.models import Equipo

    # ── 1. Filtrar por presupuesto ────────────────────────────────────────────
    qs = Equipo.objects.filter(precio__lte=Decimal(str(presupuesto)))

    # ── 2. Filtrar por tipo de equipo ─────────────────────────────────────────
    if tipo_equipo != 'ambos':
        qs = qs.filter(tipo=tipo_equipo)

    # ── 3. Filtrar opcionalmente por ubicación ────────────────────────────────
    if ubicacion:
        ciudad = ubicacion.get('ciudad', '').strip()
        departamento = ubicacion.get('departamento', '').strip()
        if ciudad:
            qs = qs.filter(ciudad__icontains=ciudad)
        elif departamento:
            qs = qs.filter(departamento__icontains=departamento)

    equipos = list(qs)

    if not equipos:
        logger.warning(
            "No se encontraron equipos con presupuesto=%.0f, tipo=%s, ubicacion=%s",
            presupuesto, tipo_equipo, ubicacion,
        )
        return []

    # ── 4. Vectorizar y calcular similitud coseno ─────────────────────────────
    query = PERFILES_USO.get(tipo_uso, tipo_uso)
    textos_equipos = [_construir_texto_equipo(e) for e in equipos]

    # Corpus: primero el query de uso, luego los equipos
    corpus = [query] + textos_equipos

    vectorizer = TfidfVectorizer(
        analyzer='word',
        ngram_range=(1, 2),
        min_df=1,
        sublinear_tf=True,
    )
    tfidf_matrix = vectorizer.fit_transform(corpus)

    # Similitud del query (índice 0) vs cada equipo (índice 1..N)
    query_vec = tfidf_matrix[0]
    equipos_matrix = tfidf_matrix[1:]
    scores = cosine_similarity(query_vec, equipos_matrix).flatten()

    # ── 5. Ordenar y retornar top-N ───────────────────────────────────────────
    indices_ordenados = np.argsort(scores)[::-1][:top_n]

    resultados = []
    for idx in indices_ordenados:
        equipo = equipos[idx]
        score = float(scores[idx])
        resultados.append({
            'id': equipo.id,
            'tipo': equipo.tipo,
            'marca': equipo.marca,
            'modelo': equipo.modelo,
            'procesador': equipo.procesador,
            'memoria_ram': equipo.memoria_ram,
            'almacenamiento': equipo.almacenamiento,
            'tarjeta_grafica': equipo.tarjeta_grafica,
            'tamanio_pantalla': equipo.tamanio_pantalla,
            'precio': float(equipo.precio),
            'tienda': equipo.tienda,
            'enlace_compra': equipo.enlace_compra,
            'ciudad': equipo.ciudad,
            'departamento': equipo.departamento,
            'score_afinidad': round(score, 4),
            'explicacion': None,  # Se rellena en la view con Gemini
        })

    return resultados
