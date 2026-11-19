# syntax=docker/dockerfile:1

# ---------- build stage: resolve dependencies into a self-contained venv ----------
FROM python:3.12-slim AS build

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

WORKDIR /build
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

# ---------- runtime stage: code + venv only, unprivileged user ----------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:${PATH}"

RUN groupadd --system --gid 10001 chat \
    && useradd --system --uid 10001 --gid chat --no-create-home chat

COPY --from=build /opt/venv /opt/venv

WORKDIR /app
COPY --chown=chat:chat app ./app

# sqlite lives on the mounted volume; the process must own it
RUN mkdir -p /app/data && chown -R chat:chat /app

USER chat
EXPOSE 8000

# liveness: the app's own health route also checks the database
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3)" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
