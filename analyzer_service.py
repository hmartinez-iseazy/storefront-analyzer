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
GENERIC_KPIS_PATH = os.getenv("GENERIC_KPIS_PATH", "./kpis_generic.json")


def load_generic_kpis() -> dict:
    """Load generic KPI configuration for MVP."""
    kpis_path = Path(GENERIC_KPIS_PATH)

    if not kpis_path.exists():
        raise FileNotFoundError(f"No se encontró configuración de KPIs genéricos: {kpis_path}")

    with open(kpis_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_available_clients() -> list[str]:
    """Get list of available client IDs (folders with images)."""
    guidelines_path = Path(GUIDELINES_DIR)
    clients = []
    supported_files = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".pdf"}

    if guidelines_path.exists():
        for item in guidelines_path.iterdir():
            if item.is_dir():
                # Check if folder has any supported image/pdf files
                has_files = any(f.suffix.lower() in supported_files for f in item.iterdir() if f.is_file())
                if has_files:
                    clients.append(item.name)

    return sorted(clients)


def load_text_guidelines(client_id: str) -> Optional[str]:
    """Load text guidelines from client's guidelines.md file."""
    client_path = Path(GUIDELINES_DIR) / client_id
    guidelines_file = client_path / "guidelines.md"

    if guidelines_file.exists():
        with open(guidelines_file, "r", encoding="utf-8") as f:
            return f.read().strip()

    return None


def build_dynamic_prompt(kpis_config: dict) -> str:
    """Build the analysis prompt dynamically based on KPIs configuration."""

    kpis = kpis_config.get("kpis", [])

    # Construir lista de categorías KPI
    kpi_categories = []
    for kpi in kpis:
        checks = kpi.get('what_to_check', [])
        checks_str = ', '.join(checks) if checks else kpi.get('description', '')
        kpi_categories.append(f"- **{kpi['name']}**: {checks_str}")

    kpis_list = "\n".join(kpi_categories)
    kpi_names = [kpi['name'] for kpi in kpis]

    prompt = f"""Responde SOLO con JSON válido.

TAREA: Evaluar el escaparate según las INSTRUCCIONES ESPECÍFICAS DEL CLIENTE.

PRIORIDAD ABSOLUTA: Las instrucciones del cliente (PUNTOS CRÍTICOS e IGNORAR) son la referencia principal.
- Si el cliente dice que algo es CRÍTICO, verifícalo.
- Si el cliente dice que algo se debe IGNORAR, no lo reportes.

REGLA DE CONFIANZA: Solo reporta algo si estás seguro de que incumple las instrucciones del cliente.

RESPUESTA JSON:
{{
  "differences": [
    {{
      "category": "<{', '.join(kpi_names)}>",
      "description": "<qué incumple de las instrucciones>",
      "action": "<qué hacer para cumplir>"
    }}
  ],
  "summary": "<resumen breve>"
}}

Si todo está correcto según las instrucciones del cliente, responde con differences = []"""

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

            # Skip configuration files
            if file_path.name in ("kpis.json", "guidelines.md"):
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
    Analyze a storefront image using Claude Vision with generic KPIs.

    Args:
        image_path: Path to the uploaded storefront image
        store_id: Identifier for the store
        client_id: Identifier for the client (determines which guidelines to use)

    Returns:
        Analysis result with KPIs and token usage
    """
    # Load generic KPIs configuration (same for all clients in MVP)
    kpis_config = load_generic_kpis()
    analysis_prompt = build_dynamic_prompt(kpis_config)

    logger.info(f"[{store_id}] Client: {client_id} | Using generic KPIs")
    logger.info(f"[{store_id}] KPI categories: {len(kpis_config.get('kpis', []))}")

    client = anthropic.Anthropic()

    # Load the storefront image
    image_data, image_media_type = load_image_as_base64(image_path)

    # Build the message content
    content = []

    # Load text guidelines first (these are the written instructions)
    text_guidelines = load_text_guidelines(client_id)
    if text_guidelines:
        content.append({
            "type": "text",
            "text": f"## INSTRUCCIONES ESPECÍFICAS DEL CLIENTE:\n\n{text_guidelines}\n\n---\n"
        })
        logger.info(f"[{store_id}] Loaded text guidelines for client {client_id}")
        logger.info(f"[{store_id}] Guidelines content:\n{text_guidelines}")
    else:
        logger.warning(f"[{store_id}] NO text guidelines found for client {client_id}")

    # Load visual guidelines from client folder
    guidelines = load_guidelines(client_id)
    if guidelines:
        content.append({
            "type": "text",
            "text": "## PLANOGRAMA/GUIDELINE VISUAL DE REFERENCIA:\n"
        })
        content.extend(guidelines)
        content.append({
            "type": "text",
            "text": "\n---\n\n## IMAGEN DEL ESCAPARATE A EVALUAR (Store ID: " + store_id + "):\n"
        })
    else:
        content.append({
            "type": "text",
            "text": f"## Imagen del escaparate a analizar (Store ID: {store_id}):\n\n⚠️ NOTA: No se ha encontrado planograma de referencia para este cliente. Evalúa la imagen aplicando criterios generales de Visual Merchandising.\n"
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
