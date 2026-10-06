# ⚙️ Backend — Sistema de Recomendación de Laptops (Django + ML)

API RESTful desarrollada con **Django 5** y **Django REST Framework (DRF)** que provee endpoints para el catálogo de equipos, algoritmo de recomendación basado en Machine Learning con **scikit-learn**, justificaciones generadas por **Google Gemini AI**, y módulos de scraping para actualización de precios.

---

## 🛠️ Tecnologías

- **Python 3.12**
- **Django 5.0 & Django REST Framework**
- **scikit-learn, NumPy & Pandas** — Motor de recomendación TF-IDF y similitud coseno.
- **google-generativeai** — Explicación de recomendaciones con el modelo Gemini 1.5 Flash.
- **PostgreSQL & SQLite** — Base de datos relacional para producción y desarrollo local.
- **BeautifulSoup4 & SerpAPI** — Recolección y scraping de información comercial de tiendas.
- **Gunicorn & WhiteNoise** — Servidor WSGI y manejo optimizado de archivos estáticos.

---

## 📁 Estructura del Backend

```text
backend/
├── core/                         # Configuración central Django
│   ├── settings.py               # Configuración de apps, DB, CORS y variables
│   ├── urls.py                   # Enrutamiento de endpoints y health check
│   └── wsgi.py                   # Punto de entrada WSGI
├── equipos/                      # Aplicación de gestión de equipos y precios
│   ├── management/commands/      # Comandos: actualizar_precios, vincular_mercadolibre
│   ├── models.py                 # Modelos Equipo e HistorialPrecio
│   ├── scraping/                 # Scrapers de Mercado Libre y tiendas locales
│   ├── serializers.py            # Serializadores para DRF
│   ├── serpapi_client.py         # Cliente SerpAPI para búsqueda en tiempo real
│   └── views.py                  # ViewSets de equipos y catálogo
├── recomendaciones/              # Motor de recomendación y LLM
│   ├── gemini_explainer.py       # Integración con Google Gemini
│   ├── ml_engine.py              # Algoritmo TF-IDF + Cosine Similarity
│   ├── models.py                 # Modelo Valoracion para feedback de usuarios
│   └── views.py                  # Endpoints /api/recomendar/, /api/catalogo/, /api/chat/
├── render.yaml                   # Infraestructura como código para Render
├── requirements.txt              # Dependencias pip
└── manage.py                     # CLI de administración Django
```

---

## ⚙️ Configuración y Variables de Entorno

Copia el archivo `.env.example` como `.env`:

```bash
cp .env.example .env
```

Configura los siguientes valores:

```env
SECRET_KEY=tu-clave-secreta
DEBUG=True
USE_SQLITE=True                  # Activa SQLite para pruebas locales sin requerir PostgreSQL

# Si usas PostgreSQL:
# DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Clave de Gemini AI:
GEMINI_API_KEY=tu_gemini_api_key

# Permitir orígenes en CORS:
ALLOWED_HOSTS=localhost,127.0.0.1
FRONTEND_URL=http://localhost:5173
```

---

## 🚀 Puesta en Marcha

1. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Ejecutar migraciones:**
   ```bash
   python manage.py migrate
   ```

3. **Crear superusuario (opcional para el panel de administración):**
   ```bash
   python manage.py createsuperuser
   ```

4. **Iniciar el servidor:**
   ```bash
   python manage.py runserver
   ```

---

## 🤖 Algoritmo de Recomendación (`ml_engine.py`)

1. **Filtrado inicial:** Filtra el universo de equipos según el presupuesto máximo tolerado y el tipo de equipo (`laptop`, `pc_escritorio` o `ambos`).
2. **Construcción de Corpus:** Combina las especificaciones clave de cada equipo (marca, modelo, CPU, RAM, GPU, pantalla, tipo de almacenamiento).
3. **TF-IDF & Cosine Similarity:** Contrasta el texto de cada equipo contra el perfil de uso seleccionado (`gaming`, `diseño`, `oficina`, `estudiante`, `programacion`, `multimedia`).
4. **Ranking y Top-N:** Ordena los equipos por puntaje de similitud y devuelve los mejores resultados con explicaciones amigables provistas por Gemini.
