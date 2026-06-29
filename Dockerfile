FROM python:3.11-slim-bookworm

# Установка системных зависимостей + инструменты MSA
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    ca-certificates \
    git \
    mafft \
    muscle \
    clustalo \
    && rm -rf /var/lib/apt/lists/*

# Опционально: NCBI Datasets CLI (раскомментируйте при необходимости)
# RUN curl -L -o /tmp/datasets.tar.gz https://ftp.ncbi.nlm.nih.gov/pub/datasets/command-line/latest/linux-amd64/datasets.tar.gz \
#     && tar -xzf /tmp/datasets.tar.gz -C /usr/local/bin/ \
#     && rm /tmp/datasets.tar.gz \
#     && chmod +x /usr/local/bin/datasets

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Создаём директории для данных
RUN mkdir -p /app/data/tasks /app/logs

# Не-root пользователь (опционально, для безопасности)
# RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
# USER appuser

EXPOSE 8000 5555

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]