FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends tzdata coreutils util-linux ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY server.py runtime.py docker_backend.py catalog.py index.html app.js style.css i18n.js ux.js ./
COPY locales ./locales
COPY assets ./assets
ENV BIND=0.0.0.0 PORT=8088 PYTHONUNBUFFERED=1 CACHEFLOW_MODE=docker
EXPOSE 8088
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8088/api/state', timeout=3)" || exit 1
CMD ["python", "server.py"]
