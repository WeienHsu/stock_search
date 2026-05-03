FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download NLTK VADER lexicon
RUN python -c "import nltk; nltk.download('vader_lexicon', quiet=True)"

COPY . .

# Persistent data volume mount point. The compose file mounts /app/data as one
# shared volume so app and worker see the same auth DB, alerts DB, settings, and caches.
RUN mkdir -p data/users data/cache/prices data/cache/news

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true"]
