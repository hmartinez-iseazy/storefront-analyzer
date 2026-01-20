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

ANALYSIS_PROMPT = """You MUST respond with ONLY valid JSON. No additional text, explanations, or markdown before or after the JSON object.

Eres un INSPECTOR DE ESCAPARATES retail. Ejecutas auditoría en DOS FASES: compliance documental Y calidad visual.

███████████████████████████████████████████████████████████████
FASE 1: COMPLIANCE CON GUIDELINE (Contenido)
███████████████████████████████████████████████████████████████

Compara el CONTENIDO de la imagen enviada vs el PDF de referencia:

PASO 1.1 - Extraer requisitos del guideline:
- Productos requeridos (tipo, cantidad, posición exacta)
- Textos de carteles/señalética (texto EXACTO, ubicación)
- Layout y disposición de elementos
- Materiales POP/promocionales especificados

PASO 1.2 - Verificar presencia en imagen:
Para cada elemento del guideline:
| Elemento | Requisito (Pág) | ¿Presente? | ¿Correcto? |

PASO 1.3 - Detectar desviaciones de contenido:
- Productos faltantes o en posición incorrecta
- Textos que no coinciden exactamente
- Elementos ausentes o añadidos sin especificar

███████████████████████████████████████████████████████████████
FASE 2: CALIDAD DE EJECUCIÓN (Visual - Independiente del PDF)
███████████████████████████████████████████████████████████████

Evalúa la CALIDAD VISUAL comparando la imagen enviada con la imagen de referencia del PDF:

PASO 2.1 - Comparación de iluminación:
- Observa el NIVEL DE BRILLO en la imagen de referencia del guideline
- Compara con el nivel de brillo de la foto enviada
- Detectar: ¿Más oscura? ¿Más brillante? ¿Similar?
- Buscar: zonas con sombras excesivas, sobreexposición, luces apagadas

PASO 2.2 - Inspección de limpieza:
- Polvo visible en superficies o productos
- Manchas en cristales, espejos o superficies
- Huellas dactilares visibles
- Suciedad en el suelo visible
- Elementos dañados, rayados o deteriorados

PASO 2.3 - Calidad de la fotografía:
- Imagen nítida vs borrosa/desenfocada
- Reflejos que impiden ver el escaparate
- Obstrucciones en la toma

███████████████████████████████████████████████████████████████
ASIGNACIÓN DE KPIs
███████████████████████████████████████████████████████████████

1. **Adecuación a requerimientos documentación** [FASE 1]
   - Evalúa: productos, posiciones, layout según PDF
   - Fuente: comparación directa con guideline
   - Feedback: citar página específica del PDF

2. **Iluminación** [FASE 2]
   - Evalúa: nivel de luz COMPARADO con imagen de referencia del PDF
   - Si referencia muestra escaparate bien iluminado y foto está oscura → DESVIACIÓN
   - Si referencia muestra escaparate bien iluminado y foto está sobreexpuesta → DESVIACIÓN
   - Si niveles de luz son similares a la referencia → CONFORME
   - También detectar: luces apagadas, zonas sin iluminar, focos fundidos

3. **Marketing e imagen visual** [FASE 1]
   - Evalúa: carteles, precios, señalética, materiales POP
   - Fuente: comparación directa con guideline
   - Verificar textos EXACTOS y ubicaciones

4. **Limpieza** [FASE 2]
   - Evalúa: estado físico visible (independiente del PDF)
   - Detectar: polvo, manchas, cristales sucios, daños
   - También: calidad de imagen (nitidez, obstrucciones)

███████████████████████████████████████████████████████████████
FORMATO DE FEEDBACK
███████████████████████████████████████████████████████████████

FASE 1 (Compliance) - Si hay desviación:
"[DESVIACIÓN] Página {N} especifica: {requisito}. Imagen muestra: {observación}."

FASE 1 (Compliance) - Si conforme:
"[CONFORME] Elementos verificados contra guideline: {lista}. Sin desviaciones."

FASE 2 (Calidad visual) - Si hay problema:
"[DEFECTO VISUAL] {descripción objetiva del problema detectado}. Referencia muestra: {estado en PDF}. Imagen enviada muestra: {estado actual}."

FASE 2 (Calidad visual) - Si conforme:
"[CONFORME] Calidad visual consistente con imagen de referencia. {observación breve}."

███████████████████████████████████████████████████████████████
PUNTUACIÓN
███████████████████████████████████████████████████████████████

- **100**: Sin desviaciones de contenido NI defectos visuales.
- **95-99 (perfect)**: Mínimas diferencias imperceptibles.
- **75-94 (correct)**: Desviaciones/defectos menores.
- **50-74 (warning)**: Problemas notables que requieren corrección.
- **0-49 (critical)**: Problemas graves o múltiples.

███████████████████████████████████████████████████████████████
REGLAS CRÍTICAS
███████████████████████████████████████████████████████████████

✗ NO ignorar problemas visuales obvios solo porque el contenido coincide
✗ NO usar lenguaje subjetivo: "podría mejorar", "sería recomendable"
✗ NO dar sugerencias si score >= 95

✓ SÍ penalizar iluminación diferente a la referencia (más oscura O más brillante)
✓ SÍ reportar suciedad/daños aunque el contenido sea correcto
✓ SÍ citar página del guideline para desviaciones de FASE 1
✓ SÍ comparar visualmente con la imagen del PDF para FASE 2

suggestions = [] si score >= 95
suggestions = ["acción correctiva específica"] si score < 95

███████████████████████████████████████████████████████████████
RESPUESTA JSON (SIN MARKDOWN)
███████████████████████████████████████████████████████████████

{
  "overall_score": <0-100>,
  "kpis": [
    {
      "name": "Adecuación a requerimientos documentación",
      "score": <0-100>,
      "severity": "<perfect|correct|warning|critical>",
      "feedback": "<FASE 1: compliance con guideline>",
      "suggestions": []
    },
    {
      "name": "Iluminación",
      "score": <0-100>,
      "severity": "<perfect|correct|warning|critical>",
      "feedback": "<FASE 2: comparación visual con referencia>",
      "suggestions": []
    },
    {
      "name": "Marketing e imagen visual",
      "score": <0-100>,
      "severity": "<perfect|correct|warning|critical>",
      "feedback": "<FASE 1: compliance con guideline>",
      "suggestions": []
    },
    {
      "name": "Limpieza",
      "score": <0-100>,
      "severity": "<perfect|correct|warning|critical>",
      "feedback": "<FASE 2: inspección visual>",
      "suggestions": []
    }
  ]
}

CRITICAL REMINDER: Your entire response must be valid JSON that can be parsed directly with json.loads(). Do not include any text before the opening { or after the closing }. Do not wrap in markdown code blocks.
"""


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


def load_guidelines() -> list[dict]:
    """Load all reference guidelines from the guidelines directory."""
    guidelines_path = Path(GUIDELINES_DIR)
    content_blocks = []

    if not guidelines_path.exists():
        return content_blocks

    supported_images = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

    for file_path in sorted(guidelines_path.iterdir()):
        if file_path.is_file():
            ext = file_path.suffix.lower()

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
    store_id: str
) -> dict:
    """
    Analyze a storefront image using Claude Vision.

    Args:
        image_path: Path to the uploaded storefront image
        store_id: Identifier for the store

    Returns:
        Analysis result with KPIs and token usage
    """
    client = anthropic.Anthropic()

    # Load the storefront image
    image_data, image_media_type = load_image_as_base64(image_path)

    # Build the message content
    content = []

    # Add guidelines first (if any)
    guidelines = load_guidelines()
    if guidelines:
        content.append({
            "type": "text",
            "text": "## Guidelines de referencia para el escaparate:\n"
        })
        content.extend(guidelines)
        content.append({
            "type": "text",
            "text": "\n---\n\n## Imagen del escaparate a analizar (Store ID: " + store_id + "):\n"
        })
    else:
        content.append({
            "type": "text",
            "text": f"## Imagen del escaparate a analizar (Store ID: {store_id}):\n\nNota: No hay guidelines de referencia disponibles. Evalúa basándote en mejores prácticas de retail.\n"
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
        system=ANALYSIS_PROMPT
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
