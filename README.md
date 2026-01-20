# Storefront Analyzer API

Microservicio para analizar fotos de escaparates de tiendas retail usando Claude Vision.

## Requisitos

- Python 3.11+
- API Key de Anthropic con acceso a Claude Vision

## Instalación

1. Clonar el repositorio y entrar al directorio:

```bash
cd storefront-analyzer
```

2. Crear y activar entorno virtual:

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# o
venv\Scripts\activate  # Windows
```

3. Instalar dependencias:

```bash
pip install -r requirements.txt
```

4. Configurar variables de entorno:

```bash
cp .env.example .env
```

Editar `.env` y agregar tu API key de Anthropic:

```
ANTHROPIC_API_KEY=tu_api_key_aqui
MODEL_NAME=claude-haiku-4-5-20251001
```

## Estructura del Proyecto

```
storefront-analyzer/
├── main.py                 # Aplicación FastAPI
├── analyzer_service.py     # Servicio de análisis con Claude Vision
├── database.py             # Operaciones SQLite
├── requirements.txt        # Dependencias Python
├── .env.example           # Template de variables de entorno
├── uploads/               # Imágenes subidas (auto-generado)
├── reference_guidelines/  # PDFs/imágenes de referencia
└── storefront_analyzer.db # Base de datos SQLite (auto-generado)
```

## Guidelines de Referencia

Coloca los archivos de referencia (guidelines del escaparate) en la carpeta `reference_guidelines/`:

- **Imágenes**: JPG, PNG, GIF, WebP
- **PDFs**: Se renderizan las páginas como imágenes para análisis visual

Estos archivos se envían a Claude junto con la imagen a analizar para comparar contra los estándares.

## Ejecución

```bash
# Desarrollo
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Producción
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Endpoints

### POST /analyze

Analiza una imagen de escaparate.

**Request:**
- `Content-Type: multipart/form-data`
- `image`: Archivo de imagen (JPG, PNG, GIF, WebP)
- `store_id`: Identificador de la tienda

```bash
curl -X POST "http://localhost:8000/analyze" \
  -F "image=@escaparate.jpg" \
  -F "store_id=STORE001"
```

**Response:**

```json
{
  "overall_score": 82,
  "kpis": [
    {
      "name": "Adecuación a requerimientos documentación",
      "score": 85,
      "severity": "correct",
      "feedback": "El escaparate cumple con la mayoría de los requisitos...",
      "suggestions": ["Ajustar la altura del cartel principal"]
    },
    {
      "name": "Iluminación",
      "score": 78,
      "severity": "correct",
      "feedback": "La iluminación general es adecuada...",
      "suggestions": []
    },
    {
      "name": "Marketing e imagen visual",
      "score": 90,
      "severity": "correct",
      "feedback": "Excelente presentación visual...",
      "suggestions": []
    },
    {
      "name": "Limpieza",
      "score": 75,
      "severity": "correct",
      "feedback": "El escaparate presenta buen nivel de limpieza...",
      "suggestions": []
    }
  ],
  "tokens_used": {
    "input": 1250,
    "output": 450
  }
}
```

### GET /analyses/{store_id}

Obtiene el historial de análisis de una tienda.

```bash
curl "http://localhost:8000/analyses/STORE001?limit=10"
```

### GET /analysis/{analysis_id}

Obtiene un análisis específico por ID.

```bash
curl "http://localhost:8000/analysis/1"
```

### GET /

Health check.

```bash
curl "http://localhost:8000/"
```

## KPIs Evaluados

| KPI | Descripción |
|-----|-------------|
| Adecuación a requerimientos documentación | Cumplimiento con guidelines y estándares de la marca |
| Iluminación | Calidad, distribución e intensidad de la iluminación |
| Marketing e imagen visual | Coherencia visual, materiales promocionales, presentación |
| Limpieza | Estado de limpieza del escaparate y superficies |

## Niveles de Severidad

| Severidad | Rango | Significado |
|-----------|-------|-------------|
| `perfect` | 95-100 | Sin problemas, cumplimiento excelente |
| `correct` | 75-94 | Aceptable, mejoras menores posibles |
| `warning` | 50-74 | Requiere atención, problemas notables |
| `critical` | 0-49 | Problemas graves, acción inmediata necesaria |

## Selección de Modelo

El servicio soporta diferentes modelos de Claude. Configura `MODEL_NAME` en `.env`:

| Modelo | Cuándo usar |
|--------|-------------|
| `claude-haiku-4-5-20251001` (default) | Alto volumen, guidelines simples, respuesta rápida, menor costo |
| `claude-sonnet-4-5-20250929` | Guidelines complejos, múltiples páginas PDF, máxima precisión |

**Recomendaciones:**

- **Haiku**: Ideal para validaciones rutinarias donde los guidelines son claros y las desviaciones son obvias. Procesa más rápido y a menor costo.

- **Sonnet**: Usar cuando:
  - El PDF de guidelines tiene muchas páginas con detalles específicos
  - Se requiere detectar diferencias sutiles de iluminación o posicionamiento
  - Los análisis previos con Haiku no detectaron problemas conocidos

```bash
# Cambiar a Sonnet para mayor precisión
MODEL_NAME=claude-sonnet-4-5-20250929
```

## Documentación API

Con el servidor corriendo, accede a:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Base de Datos

SQLite con tabla `analyses`:

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | INTEGER | Primary key |
| store_id | TEXT | Identificador de tienda |
| image_filename | TEXT | Nombre del archivo guardado |
| result_json | TEXT | Resultado del análisis (JSON) |
| tokens_input | INTEGER | Tokens de entrada usados |
| tokens_output | INTEGER | Tokens de salida usados |
| created_at | TEXT | Timestamp ISO 8601 |
