# One image for api, worker, beat, egress and the three bots (different commands).
FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
# FFmpeg (Debian package, LGPL/GPL) merges separate video and audio streams; it runs as a separate program.
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml ./
COPY backend ./backend
COPY bots ./bots
COPY workers ./workers
COPY storage ./storage
COPY infrastructure ./infrastructure
RUN pip install . && useradd --uid 10001 --create-home app && mkdir -p /data/files && chown 10001:10001 /data/files
COPY alembic.ini ./
USER 10001:10001
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log", "--no-proxy-headers"]
