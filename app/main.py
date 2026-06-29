from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, Request
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pathlib import Path
import logging
import os
import shutil
from datetime import datetime
from typing import Optional

from app.config import get_settings
from app.database import get_db, init_db, SessionLocal
from app.models import Task
from app.schemas import MSARequest, TaskCreateResponse, TaskStatusResponse
from app.tasks import run_msa_pipeline, celery_app

settings = get_settings()

# Templates
templates = Jinja2Templates(directory="app/templates")

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("msa_api")

app = FastAPI(
    title="BioMSA Server — Множественное выравнивание геномных последовательностей",
    description="Асинхронный веб-сервис для скачивания, выравнивания и построения консенсуса последовательностей из NCBI, Ensembl и др.",
    version="0.9.0-prototype",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS (для будущего фронтенда)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    logger.info("Starting BioMSA Server...")
    init_db()
    # Создаём директории
    Path(settings.DATA_DIR).mkdir(parents=True, exist_ok=True)
    Path(settings.LOG_DIR).mkdir(parents=True, exist_ok=True)
    logger.info("Database initialized. Directories ready.")

@app.get("/", response_class=HTMLResponse, tags=["UI"])
async def serve_ui(request: Request):
    """Красивый веб-интерфейс BioMSA"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/msa", response_model=TaskCreateResponse, tags=["MSA Pipeline"])
async def create_msa_task(
    request: MSARequest,
    db: Session = Depends(get_db)
):
    """
    Создаёт новую задачу на множественное выравнивание.
    
    - **organism**: Обязательно. Например "Escherichia coli" или "SARS-CoV-2"
    - **gene**: Опционально. Если не указано — пытаемся скачать геномы (ограничено)
    - **sources**: Список источников (пока в основном ncbi + mock)
    - **alignment_tool**: mafft | clustalo | muscle
    - **use_mock_data**: True — для быстрого теста без API
    """
    # Создаём запись в БД
    task = Task(
        organism=request.organism,
        gene=request.gene,
        sources=[s.value for s in request.sources],
        alignment_tool=request.alignment_tool.value,
        params={
            "max_sequences": request.max_sequences,
            "use_mock_data": request.use_mock_data,
            "sequence_type": request.sequence_type
        },
        status="PENDING"
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # Отправляем в Celery
    run_msa_pipeline.delay(
        task_id=task.id,
        params={
            "organism": request.organism,
            "gene": request.gene,
            "sources": [s.value for s in request.sources],
            "alignment_tool": request.alignment_tool.value,
            "max_sequences": request.max_sequences,
            "use_mock_data": request.use_mock_data,
            "sequence_type": request.sequence_type
        }
    )
    
    logger.info(f"Created task {task.id} for {request.organism} / {request.gene}")
    
    return TaskCreateResponse(
        task_id=task.id,
        status="PENDING",
        message="Задача принята в обработку. Отслеживайте статус по /status/" + task.id
    )

@app.get("/status/{task_id}", response_model=TaskStatusResponse, tags=["MSA Pipeline"])
async def get_task_status(task_id: str, db: Session = Depends(get_db)):
    """Получить текущий статус задачи и пути к результатам"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    
    return TaskStatusResponse(**task.to_dict())

@app.get("/download/{task_id}/{filename}", tags=["Results"])
async def download_result(task_id: str, filename: str, db: Session = Depends(get_db)):
    """
    Скачать файл результата.
    Доступные имена: input.fasta, aligned.fasta, consensus.fasta, pipeline.log
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task or not task.result_files:
        raise HTTPException(status_code=404, detail="Результаты ещё не готовы или задача не найдена")
    
    file_map = {
        "input.fasta": task.result_files.get("input_fasta"),
        "aligned.fasta": task.result_files.get("aligned_fasta"),
        "consensus.fasta": task.result_files.get("consensus_fasta"),
        "pipeline.log": task.result_files.get("log_file"),
    }
    
    file_path = file_map.get(filename)
    if not file_path or not Path(file_path).exists():
        raise HTTPException(status_code=404, detail=f"Файл {filename} не найден для задачи {task_id}")
    
    media = "text/plain"
    if filename.endswith(".fasta"):
        media = "text/x-fasta"
    
    return FileResponse(
        path=file_path,
        filename=f"{task.organism}_{task.gene or 'genome'}_{filename}",
        media_type=media
    )

@app.get("/tasks", tags=["Admin"])
async def list_recent_tasks(limit: int = 20, db: Session = Depends(get_db)):
    """Список последних задач (для отладки)"""
    tasks = db.query(Task).order_by(Task.created_at.desc()).limit(limit).all()
    return [t.to_dict() for t in tasks]

@app.delete("/tasks/{task_id}", tags=["Admin"])
async def delete_task(task_id: str, db: Session = Depends(get_db)):
    """Удалить задачу и её файлы (осторожно!)"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(404, "Not found")
    
    if task.result_files and "task_dir" in task.result_files:
        task_dir = Path(task.result_files["task_dir"])
        if task_dir.exists():
            shutil.rmtree(task_dir, ignore_errors=True)
    
    db.delete(task)
    db.commit()
    return {"message": f"Task {task_id} deleted"}

# Health check для Docker / k8s
@app.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}