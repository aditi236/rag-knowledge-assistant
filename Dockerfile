FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    FASTEMBED_CACHE_PATH=/opt/models INDEX_DIR=/data/index

WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Bake the embedding model into the image so containers start fast and offline.
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('BAAI/bge-small-en-v1.5')"

COPY app ./app
COPY data ./data

RUN useradd --create-home appuser && mkdir /data && chown -R appuser /data /opt/models
USER appuser

EXPOSE 8000
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
CMD ["uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8000"]
