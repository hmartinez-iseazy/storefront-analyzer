import anthropic
import base64
import json
import logging
import os
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GUIDELINES_DIR = os.getenv("GUIDELINES_DIR", "./reference_guidelines")
MODEL_NAME = os.getenv("MODEL_NAME", "claude-haiku-4-5-20251001")


def load_client_kpis(client_id: str) -> dict:
    """Load KPI configuration for a specific client."""
    kpis_path = Path(GUIDELINES_DIR) / client_id / "kpis.json"

    if not kpis_path.exists():
        raise FileNotFoundError(f"No se encontró configuración de KPIs para cliente: {client_id}")

    with open(kpis_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_available_clients() -> list[str]:
    """Get list of available client IDs."""
    guidelines_path = Path(GUIDELINES_DIR)
    clients = []

    if guidelines_path.exists():
        for item in guidelines_path.iterdir():
            if item.is_dir() and (item / "kpis.json").exists():
                clients.append(item.name)

    return sorted(clients)


def build_dynamic_prompt(kpis_config: dict) -> str:
    """Build the analysis prompt dynamically based on client categories."""

    client_name = kpis_config.get("client_name", "Cliente")
    categories = kpis_config.get("kpis", [])  # Now used as categories for classification

    # Construir lista de categorías
    categories_list = "\n".join([f"- **{cat['name']}**: {cat['description']}" for cat in categories])
    categories_names = [cat['name'] for cat in categories]

    prompt = f"""You MUST respond with ONLY valid JSON. No additional text, explanations, or markdown before or after the JSON object.

███████████████████████████████████████████████████████████████
PRINCIPIO FUNDAMENTAL - ERES UN INSPECTOR RIGUROSO
███████████████████████████████████████████████████████████████

EL GUIDELINE (PDF/IMAGEN DE REFERENCIA) ES LA VERDAD ABSOLUTA.

Tu trabajo es comparar la imagen enviada con el guideline y detectar TODAS las diferencias.
Debes ser EXTREMADAMENTE RIGUROSO y CRÍTICO. Si algo no está EXACTAMENTE igual que en el guideline, es una diferencia que debe reportarse.

IMPORTANTE:
- Si el guideline muestra cables OCULTOS y la imagen tiene cables VISIBLES → CRÍTICO
- Si el guideline muestra pantallas ENCENDIDAS y la imagen tiene pantallas APAGADAS → CRÍTICO
- Si hay BASURA, objetos ajenos, suciedad que NO está en el guideline → CRÍTICO
- Cualquier desorden evidente comparado con el guideline → penalización SEVERA

NO seas benevolente. NO redondees hacia arriba. Si ves un desastre, el score debe reflejarlo.

███████████████████████████████████████████████████████████████
ESCALA DE SIMILITUD (similarity_score)
███████████████████████████████████████████████████████████████

El similarity_score es una evaluación GLOBAL de cuánto se parece la imagen al guideline:

- **100**: IDÉNTICO al guideline. Ninguna diferencia visible.
- **90-99**: Casi perfecto. Solo diferencias mínimas, imperceptibles.
- **70-89**: Aceptable. Algunas diferencias menores pero el aspecto general es similar.
- **50-69**: Deficiente. Diferencias notables que afectan la imagen.
- **30-49**: Muy deficiente. Múltiples problemas graves.
- **0-29**: INACEPTABLE. Desastre total. Muy diferente al guideline.

EJEMPLOS DE SCORES BAJOS:
- Pantallas de dispositivos apagadas cuando deberían estar encendidas → -30 puntos mínimo
- Cables desordenados/visibles cuando deberían estar ocultos → -25 puntos mínimo
- Basura, vasos, papeles que no están en el guideline → -20 puntos por cada objeto
- Productos en posiciones muy diferentes → -15 puntos por producto

Si una imagen tiene múltiples problemas graves (pantallas apagadas + cables sueltos + basura),
el score debe ser MUY BAJO (20-40 máximo).

███████████████████████████████████████████████████████████████
PROCESO DE ANÁLISIS
███████████████████████████████████████████████████████████████

PASO 1: Observa el guideline de referencia
- Memoriza EXACTAMENTE cómo se ve cada elemento
- Estado de pantallas/dispositivos (encendidos/apagados)
- Posición y visibilidad de cables
- Limpieza y orden general
- Posición exacta de cada producto

PASO 2: Compara la imagen enviada con OJO CRÍTICO
- ¿Las pantallas están en el MISMO estado?
- ¿Los cables están IGUAL de ordenados/ocultos?
- ¿Hay objetos que NO deberían estar (basura, vasos, papeles)?
- ¿Los productos están en las MISMAS posiciones?

PASO 3: Lista TODAS las diferencias encontradas
- Sé exhaustivo, no omitas nada
- Clasifica cada diferencia en una categoría
- Asigna un impacto realista (minor/moderate/high/critical)

███████████████████████████████████████████████████████████████
CATEGORÍAS PARA CLASIFICAR DIFERENCIAS
███████████████████████████████████████████████████████████████

{categories_list}

███████████████████████████████████████████████████████████████
NIVELES DE IMPACTO
███████████████████████████████████████████████████████████████

- **critical**: Problema gravísimo. Inmediatamente visible. Inaceptable.
  Ejemplos: pantallas apagadas, basura visible, cables muy desordenados

- **high**: Problema grave. Claramente visible. Requiere corrección urgente.
  Ejemplos: productos en posición incorrecta, carteles torcidos

- **moderate**: Problema notable. Visible al observar con atención.
  Ejemplos: pequeñas diferencias de posición, iluminación ligeramente diferente

- **minor**: Problema menor. Apenas perceptible.
  Ejemplos: mínimas diferencias de ángulo, pequeñas variaciones de color

███████████████████████████████████████████████████████████████
REGLAS CRÍTICAS
███████████████████████████████████████████████████████████████

✗ NUNCA seas benevolente con problemas evidentes
✗ NUNCA des un score alto si hay problemas graves visibles
✗ NUNCA ignores basura, suciedad u objetos que no están en el guideline
✗ NUNCA asumas que "está bien" si no es IDÉNTICO

✓ SÍ penaliza severamente los problemas críticos
✓ SÍ reporta TODAS las diferencias que veas
✓ SÍ da scores muy bajos (20-40) si la imagen es un desastre
✓ SÍ sé específico en las descripciones de los problemas

███████████████████████████████████████████████████████████████
RESPUESTA JSON
███████████████████████████████████████████████████████████████

{{
  "similarity_score": <0-100>,
  "similarity_verdict": "<perfect|acceptable|deficient|critical>",
  "differences": [
    {{
      "description": "<descripción específica de la diferencia>",
      "category": "<una de: {', '.join(categories_names)}>",
      "impact": "<minor|moderate|high|critical>",
      "action": "<acción específica para igualar al guideline>"
    }}
  ],
  "category_summary": {{
    {', '.join([f'"{cat}": {{"issues": "<número>", "max_impact": "<minor|moderate|high|critical|null>"}}' for cat in categories_names])}
  }}
}}

NOTAS:
- Si no hay diferencias: differences = [], similarity_score = 100, similarity_verdict = "perfect"
- similarity_verdict: "perfect" (90-100), "acceptable" (70-89), "deficient" (50-69), "critical" (0-49)
- category_summary.max_impact es null si issues = 0 para esa categoría

CRITICAL: Be HARSH and REALISTIC. If you see a mess (screens off, cables everywhere, trash), the score MUST be very low (20-40). Do NOT be lenient."""

    return prompt



def get_image_media_type(file_path: str) -> str:
    """Get the media type based on file extension."""
    ext = Path(file_path).suffix.lower()
    media_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp"
    }
    return media_types.get(ext, "image/jpeg")


def load_image_as_base64(file_path: str) -> tuple[str, str]:
    """Load an image file and return its base64 encoding and media type."""
    media_type = get_image_media_type(file_path)
    with open(file_path, "rb") as f:
        data = base64.standard_b64encode(f.read()).decode("utf-8")
    return data, media_type


def extract_images_from_pdf(pdf_path: str) -> list[tuple[str, str]]:
    """Extract images from a PDF file and return as base64 encoded data."""
    images = []
    doc = fitz.open(pdf_path)

    for page_num in range(len(doc)):
        page = doc[page_num]
        image_list = page.get_images()

        for img_index, img in enumerate(image_list):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]

            media_type = f"image/{image_ext}" if image_ext != "jpg" else "image/jpeg"
            data = base64.standard_b64encode(image_bytes).decode("utf-8")
            images.append((data, media_type))

    doc.close()
    return images


def render_pdf_pages_as_images(pdf_path: str, dpi: int = 150) -> list[tuple[str, str]]:
    """Render PDF pages as images."""
    images = []
    doc = fitz.open(pdf_path)

    for page_num in range(len(doc)):
        page = doc[page_num]
        # Render page to image
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat)
        image_bytes = pix.tobytes("png")

        data = base64.standard_b64encode(image_bytes).decode("utf-8")
        images.append((data, "image/png"))

    doc.close()
    return images


def load_guidelines(client_id: str) -> list[dict]:
    """Load all reference guidelines from the client's directory."""
    client_path = Path(GUIDELINES_DIR) / client_id
    content_blocks = []

    if not client_path.exists():
        return content_blocks

    supported_images = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

    for file_path in sorted(client_path.iterdir()):
        if file_path.is_file():
            ext = file_path.suffix.lower()

            # Skip kpis.json configuration file
            if file_path.name == "kpis.json":
                continue

            if ext in supported_images:
                data, media_type = load_image_as_base64(str(file_path))
                content_blocks.append({
                    "type": "text",
                    "text": f"[Guideline de referencia: {file_path.name}]"
                })
                content_blocks.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": data
                    }
                })

            elif ext == ".pdf":
                # Render PDF pages as images for visual analysis
                pdf_images = render_pdf_pages_as_images(str(file_path))
                if pdf_images:
                    content_blocks.append({
                        "type": "text",
                        "text": f"[Guideline PDF: {file_path.name} - {len(pdf_images)} páginas]"
                    })
                    for i, (data, media_type) in enumerate(pdf_images):
                        content_blocks.append({
                            "type": "text",
                            "text": f"[Página {i + 1}]"
                        })
                        content_blocks.append({
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": data
                            }
                        })

    return content_blocks


async def analyze_storefront(
    image_path: str,
    store_id: str,
    client_id: str
) -> dict:
    """
    Analyze a storefront image using Claude Vision.

    Args:
        image_path: Path to the uploaded storefront image
        store_id: Identifier for the store
        client_id: Identifier for the client (determines which KPIs and guidelines to use)

    Returns:
        Analysis result with KPIs and token usage
    """
    # Load client KPIs configuration
    kpis_config = load_client_kpis(client_id)
    analysis_prompt = build_dynamic_prompt(kpis_config)

    logger.info(f"[{store_id}] Using client: {client_id} ({kpis_config.get('client_name', 'Unknown')})")
    logger.info(f"[{store_id}] KPIs to evaluate: {len(kpis_config.get('kpis', []))}")

    client = anthropic.Anthropic()

    # Load the storefront image
    image_data, image_media_type = load_image_as_base64(image_path)

    # Build the message content
    content = []

    # Add guidelines first (if any)
    guidelines = load_guidelines(client_id)
    if guidelines:
        content.append({
            "type": "text",
            "text": f"## Guidelines de referencia para {kpis_config.get('client_name', 'el escaparate')}:\n"
        })
        content.extend(guidelines)
        content.append({
            "type": "text",
            "text": "\n---\n\n## Imagen del escaparate a analizar (Store ID: " + store_id + "):\n"
        })
    else:
        content.append({
            "type": "text",
            "text": f"## Imagen del escaparate a analizar (Store ID: {store_id}):\n\nNota: No hay guidelines de referencia disponibles para {kpis_config.get('client_name', 'este cliente')}. Evalúa basándote en las descripciones de los KPIs.\n"
        })

    # Add the storefront image to analyze
    content.append({
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": image_media_type,
            "data": image_data
        }
    })

    # Call Claude API with temperature=0 for deterministic output
    message = client.messages.create(
        model=MODEL_NAME,
        max_tokens=4096,
        temperature=0,
        messages=[
            {
                "role": "user",
                "content": content
            }
        ],
        system=analysis_prompt
    )

    # Extract token usage
    tokens_input = message.usage.input_tokens
    tokens_output = message.usage.output_tokens

    # Get raw response
    raw_response = message.content[0].text

    # Log raw response for debugging
    logger.info(f"[{store_id}] Model: {MODEL_NAME}")
    logger.info(f"[{store_id}] Tokens - Input: {tokens_input}, Output: {tokens_output}")
    logger.debug(f"[{store_id}] Raw response:\n{raw_response}")

    # Parse the response
    response_text = raw_response.strip()

    # Clean up response if it contains markdown code blocks
    if response_text.startswith("```"):
        logger.warning(f"[{store_id}] Response contained markdown code blocks, cleaning up")
        lines = response_text.split("\n")
        # Remove first line (```json) and last line (```)
        lines = [l for l in lines if not l.startswith("```")]
        response_text = "\n".join(lines)

    # Try to extract JSON if there's text before/after
    if not response_text.startswith("{"):
        logger.warning(f"[{store_id}] Response doesn't start with '{{', attempting to extract JSON")
        start_idx = response_text.find("{")
        end_idx = response_text.rfind("}") + 1
        if start_idx != -1 and end_idx > start_idx:
            response_text = response_text[start_idx:end_idx]
            logger.info(f"[{store_id}] Extracted JSON from position {start_idx} to {end_idx}")

    try:
        result = json.loads(response_text)
        logger.info(f"[{store_id}] Successfully parsed JSON response")
    except json.JSONDecodeError as e:
        # Log the full raw response for debugging
        logger.error(f"[{store_id}] JSON parse error: {str(e)}")
        logger.error(f"[{store_id}] Raw response that failed to parse:\n{raw_response}")
        logger.error(f"[{store_id}] Cleaned response that failed:\n{response_text}")

        # Return error result with details
        result = {
            "overall_score": 0,
            "kpis": [
                {
                    "name": "Adecuación a requerimientos documentación",
                    "score": 0,
                    "severity": "critical",
                    "feedback": f"Error de parsing JSON: {str(e)}",
                    "suggestions": ["Reintentar el análisis", "Considerar usar modelo Sonnet para mayor precisión"]
                },
                {
                    "name": "Iluminación",
                    "score": 0,
                    "severity": "critical",
                    "feedback": "Análisis no completado debido a error de formato",
                    "suggestions": []
                },
                {
                    "name": "Marketing e imagen visual",
                    "score": 0,
                    "severity": "critical",
                    "feedback": "Análisis no completado debido a error de formato",
                    "suggestions": []
                },
                {
                    "name": "Limpieza",
                    "score": 0,
                    "severity": "critical",
                    "feedback": "Análisis no completado debido a error de formato",
                    "suggestions": []
                }
            ],
            "error": {
                "type": "JSON_PARSE_ERROR",
                "message": str(e),
                "model": MODEL_NAME,
                "raw_response_preview": raw_response[:1000] if len(raw_response) > 1000 else raw_response
            }
        }

    # Add token usage to result
    result["tokens_used"] = {
        "input": tokens_input,
        "output": tokens_output
    }

    return result, tokens_input, tokens_output
