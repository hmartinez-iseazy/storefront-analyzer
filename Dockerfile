FROM python:3.12-slim

WORKDIR /app

# Runtime libs needed by PyMuPDF (libmupdf bundled but requires these on slim)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py analyzer_service.py database.py kpis_generic.json ./
COPY static/ ./static/
COPY reference_guidelines/ ./reference_guidelines/

# /app/uploads para imágenes subidas, /data para la base de datos SQLite
RUN mkdir -p /app/uploads /data

ENV DATABASE_PATH=/data/storefront_analyzer.db

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
