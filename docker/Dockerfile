FROM python:3.13-slim

# Instala dependências do sistema (para lxml, psycopg2, etc.)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    gcc \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Cria diretório de trabalho
WORKDIR /app

# Copia requirements e instala dependências Python
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copia o restante do código
COPY . .

# Expõe a porta padrão do FastAPI/Uvicorn
EXPOSE 8000

# Variáveis de ambiente (ajuste conforme necessário)
ENV PYTHONUNBUFFERED=1

# Comando de inicialização (ajuste se necessário)
CMD ["gunicorn", "src.app.web.main:app", "--workers", "1", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8080"]