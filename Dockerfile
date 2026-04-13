# ============================================
# Stage 1: Build dependencies
# ============================================
FROM python:3.11-slim as builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Pre-download Whisper model (base model ~140MB)
RUN python -c "import whisper; whisper.load_model('base')"

# ============================================
# Stage 2: Base image (slow — rebuild only when deps change)
# ============================================
FROM python:3.11-slim as base

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY --from=builder /root/.cache/whisper /root/.cache/whisper

# ============================================
# Stage 3: App image (fast — only code changes)
# ============================================
FROM base as production

COPY server.py .
COPY lib/ lib/

EXPOSE 3001

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:3001/api/health')"

CMD ["python", "server.py"]
