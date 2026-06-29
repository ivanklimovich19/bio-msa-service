# 🧬 BioMSA Server — Асинхронный веб-сервис для множественного выравнивания последовательностей

Полноценный прототип серверного приложения для скачивания полногеномных/генных последовательностей из публичных баз, их объединения, множественного выравнивания (MSA) и построения консенсуса.

**Технологии:** FastAPI + Celery + Redis + PostgreSQL + Docker + Biopython + MAFFT/Clustal Omega/MUSCLE

---

## 🚀 Быстрый старт (Docker Compose)

```bash
# 1. Клонируйте / скопируйте проект
cd msa_bio_service

# 2. Создайте .env (опционально)
cp .env.example .env
# Отредактируйте NCBI_EMAIL на свой (рекомендуется)

# 3. Запустите всё
docker compose up -d --build

# 4. Проверьте, что сервисы поднялись
docker compose ps
```

**Доступные сервисы после запуска:**
- **🌟 Красивый веб-интерфейс:** http://localhost:8000 (главная страница — современный UI)
- **API + Swagger UI:** http://localhost:8000/docs
- **Flower (мониторинг задач):** http://localhost:5555
- **PostgreSQL:** localhost:5432 (user: msauser, pass: msapass123, db: msa_db)
- **Redis:** localhost:6379

---

## 📡 API Endpoints

### 1. Создать задачу (POST /msa)

```bash
curl -X POST "http://localhost:8000/msa" \
  -H "Content-Type: application/json" \
  -d '{
    "organism": "Escherichia coli",
    "gene": "rpoB",
    "sources": ["ncbi"],
    "alignment_tool": "mafft",
    "max_sequences": 50,
    "use_mock_data": true,
    "sequence_type": "gene"
  }'
```

**Важно:** 
- В веб-интерфейсе (http://localhost:8000) по умолчанию включён **Демо-режим** — работает мгновенно без интернета.
- Для реальных данных из NCBI снимите галочку "Демо-режим" (требуется интернет).

### 2. Проверить статус (GET /status/{task_id})

```bash
curl http://localhost:8000/status/ВАШ_TASK_ID
```

### 3. Скачать результаты

```bash
# Выровненный FASTA
curl -O http://localhost:8000/download/ВАШ_TASK_ID/aligned.fasta

# Консенсус
curl -O http://localhost:8000/download/ВАШ_TASK_ID/consensus.fasta

# Исходные данные
curl -O http://localhost:8000/download/ВАШ_TASK_ID/input.fasta
```

---

## 🏗️ Архитектура

Полная диаграмма в `docs/architecture.dot` (Graphviz).

**Ключевые компоненты:**

1. **FastAPI** — REST API, валидация, работа с БД
2. **Celery Worker** — фоновая обработка (скачивание может занимать минуты/часы)
3. **Адаптеры** (`app/adapters/`) — модульная система для NCBI, Ensembl, EBI (сейчас реализован NCBI + Mock)
4. **Pipeline**:
   - Скачивание → Объединение FASTA → MSA (внешний инструмент) → Консенсус (Biopython) → Сохранение
5. **Хранение результатов**: `/app/data/tasks/{task_id}/` (маунтится как volume)

---

## ⚙️ Настройка и расширение

### Добавление нового источника данных
1. Создайте `app/adapters/your_adapter.py`
2. Наследуйтесь от `BaseDataAdapter`
3. Реализуйте `fetch_sequences(...)`
4. Зарегистрируйте в `app/adapters/__init__.py`

### Использование NCBI Datasets CLI (рекомендуется для геномов)
Раскомментируйте блок в `Dockerfile` и реализуйте адаптер через `subprocess` вызова `datasets`.

### Ограничения прототипа
- Для whole-genome выравнивания тысяч последовательностей нужны очень мощные серверы (сотни ГБ RAM).
- Текущая реализация ориентирована на **гены** (rpoB, 16S, recA и т.д.) — это реалистично.
- Реальные скачивания из NCBI ограничены rate-limit (рекомендуется API-ключ).

---

## 🧪 Примеры использования

### Демо-режим (без интернета)
```json
{
  "organism": "Bacillus subtilis",
  "gene": "gyrB",
  "use_mock_data": true,
  "max_sequences": 30
}
```

### Реальный запрос к NCBI (нужен интернет + EMAIL)
```json
{
  "organism": "Mycobacterium tuberculosis",
  "gene": "rpoB",
  "use_mock_data": false,
  "max_sequences": 100,
  "alignment_tool": "mafft"
}
```

---

## 🚀 Деплой на Railway (рекомендуется)

1. Залей код на GitHub
2. Зайди на [railway.app](https://railway.app) и создай новый проект
3. Выбери **Deploy from GitHub repo**
4. Railway автоматически соберёт Docker-образ
5. Добавь в проект два сервиса:
   - **Postgres** (из шаблонов)
   - **Redis** (из шаблонов)
6. В переменных окружения основного сервиса укажи:
   - `DATABASE_URL` — возьми из Railway Postgres
   - `REDIS_URL` и `CELERY_BROKER_URL` — возьми из Railway Redis
7. Запусти деплой

После деплоя у тебя будет публичная ссылка на работающий сервис.

---

## 📁 Структура проекта

```
msa_bio_service/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── README.md
├── docs/
│   └── architecture.dot
├── app/
│   ├── main.py              # FastAPI приложение + эндпоинты
│   ├── config.py            # Pydantic Settings
│   ├── database.py          # SQLAlchemy engine + Base
│   ├── models.py            # Модель Task
│   ├── schemas.py           # Pydantic схемы запросов/ответов
│   ├── tasks.py             # Celery задачи + pipeline
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── mock_adapter.py
│   │   ├── ncbi_adapter.py
│   │   ├── ensembl_adapter.py
│   │   └── ebi_adapter.py
│   └── utils/
│       └── sequence_utils.py  # merge, alignment, consensus
└── data/                    # (создаётся автоматически)
```

---

## 🛠️ Разработка и отладка

```bash
# Локальный запуск без Docker (требует Redis + Postgres + инструменты MSA)
uvicorn app.main:app --reload
celery -A app.tasks.celery_app worker --loglevel=info

# Просмотр логов
docker compose logs -f web
docker compose logs -f worker

# Очистка всех данных
docker compose down -v
```

---

## 📌 Следующие шаги (рекомендации)

- [ ] Реализовать полноценный Ensembl и EBI адаптеры
- [ ] Добавить NCBI Datasets CLI адаптер для целых геномов
- [ ] Добавить веб-интерфейс (Streamlit / React / NiceGUI)
- [ ] Добавить S3-совместимое хранилище вместо локальной ФС
- [ ] Улучшить консенсус (взвешенный, с учётом качества)
- [ ] Добавить тесты (pytest) и CI
- [ ] Rate limiting + аутентификация пользователей

---

**Автор прототипа:** Grok (xAI) по запросу пользователя  
**Дата:** Июнь 2026  
**Статус:** Рабочий прототип (демо + реальные данные из NCBI)

Удачи в биоинформатических исследованиях! 🧬🔬

Если нужны улучшения, дополнительные адаптеры или фронтенд — пишите!