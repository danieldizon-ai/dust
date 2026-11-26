# Dust as a private checking service: no model, no network calls, no request logging.
#   docker build -t dust .
#   docker run --rm -p 127.0.0.1:8381:8381 -e DUST_API_TOKEN="$(openssl rand -hex 24)" dust
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md LICENSE NOTICE ./
COPY src ./src
RUN pip install --no-cache-dir . && useradd --system --uid 10001 dust
USER dust
EXPOSE 8381
HEALTHCHECK CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8381/healthz')"
CMD ["dust", "serve", "--host", "0.0.0.0", "--port", "8381", "--token-env", "DUST_API_TOKEN"]
