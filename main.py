import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

load_dotenv()

from analyzer_service import analyze_storefront
from database import get_analyses_by_store, get_analysis, init_db, save_analysis

UPLOADS_DIR = os.getenv("UPLOADS_DIR", "./uploads")
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize resources on startup."""
    # Ensure uploads directory exists
    Path(UPLOADS_DIR).mkdir(parents=True, exist_ok=True)

    # Initialize database
    await init_db()

    yield


app = FastAPI(
    title="Storefront Analyzer API",
    description="API para analizar escaparates de tiendas retail usando Claude Vision",
    version="1.0.0",
    lifespan=lifespan
)


class KPI(BaseModel):
    name: str
    score: int
    severity: str
    feedback: str
    suggestions: list[str]


class TokensUsed(BaseModel):
    input: int
    output: int


class AnalysisResponse(BaseModel):
    overall_score: int
    kpis: list[KPI]
    tokens_used: TokensUsed


class AnalysisRecord(BaseModel):
    id: int
    store_id: str
    image_filename: str
    result: AnalysisResponse
    created_at: str


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "service": "Storefront Analyzer API",
        "status": "healthy",
        "version": "1.0.0"
    }


@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_endpoint(
    image: UploadFile = File(..., description="Imagen del escaparate a analizar"),
    store_id: str = Form(..., description="Identificador de la tienda")
):
    """
    Analiza una imagen de escaparate comparándola con las guidelines de referencia.

    - **image**: Imagen del escaparate (JPG, PNG, GIF, WebP)
    - **store_id**: Identificador único de la tienda

    Retorna puntuaciones para 4 KPIs:
    - Adecuación a requerimientos documentación
    - Iluminación
    - Marketing e imagen visual
    - Limpieza
    """
    # Validate API key is configured
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise HTTPException(
            status_code=500,
            detail="ANTHROPIC_API_KEY no está configurada"
        )

    # Validate file extension
    file_ext = Path(image.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de archivo no soportado. Formatos permitidos: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Read and validate file size
    content = await image.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Archivo demasiado grande. Tamaño máximo: {MAX_FILE_SIZE // (1024*1024)}MB"
        )

    # Generate unique filename
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    filename = f"{store_id}_{timestamp}_{unique_id}{file_ext}"
    file_path = Path(UPLOADS_DIR) / filename

    # Save uploaded file
    try:
        with open(file_path, "wb") as f:
            f.write(content)
    except IOError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al guardar la imagen: {str(e)}"
        )

    # Perform analysis
    try:
        result, tokens_input, tokens_output = await analyze_storefront(
            str(file_path),
            store_id
        )
    except Exception as e:
        # Clean up file on error
        file_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error durante el análisis: {str(e)}"
        )

    # Save to database
    try:
        await save_analysis(
            store_id=store_id,
            image_filename=filename,
            result_json=result,
            tokens_input=tokens_input,
            tokens_output=tokens_output
        )
    except Exception as e:
        # Log error but don't fail the request
        print(f"Warning: Failed to save analysis to database: {e}")

    return result


@app.get("/analyses/{store_id}", response_model=list[AnalysisRecord])
async def get_store_analyses(store_id: str, limit: int = 50):
    """
    Obtiene el historial de análisis para una tienda específica.

    - **store_id**: Identificador de la tienda
    - **limit**: Número máximo de resultados (default: 50)
    """
    analyses = await get_analyses_by_store(store_id, limit)

    return [
        {
            "id": a["id"],
            "store_id": a["store_id"],
            "image_filename": a["image_filename"],
            "result": a["result_json"],
            "created_at": a["created_at"]
        }
        for a in analyses
    ]


@app.get("/analysis/{analysis_id}")
async def get_single_analysis(analysis_id: int):
    """
    Obtiene un análisis específico por su ID.

    - **analysis_id**: ID del análisis
    """
    analysis = await get_analysis(analysis_id)

    if not analysis:
        raise HTTPException(
            status_code=404,
            detail="Análisis no encontrado"
        )

    return {
        "id": analysis["id"],
        "store_id": analysis["store_id"],
        "image_filename": analysis["image_filename"],
        "result": analysis["result_json"],
        "created_at": analysis["created_at"]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
