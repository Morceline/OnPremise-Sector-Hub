# Imagem enxuta: slim reduz superfície de ataque e tamanho em disco,
# importante já que tudo roda na máquina do próprio usuário.
FROM python:3.12-slim

WORKDIR /app

# Dependências de sistema mínimas para compilar libs nativas (ex: alguns
# parsers de PDF). Removidas do cache do apt na mesma camada para não
# inflar a imagem final.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Boas práticas de segurança: não rodar o processo como root dentro do container.
RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/app/data \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Healthcheck nativo do Docker: permite que `docker compose ps` e
# orquestradores saibam se a API está realmente respondendo, não só "up".
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=3)" || exit 1

CMD ["fastapi", "run", "app/main.py", "--port", "8000"]
