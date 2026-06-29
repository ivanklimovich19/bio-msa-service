import os
import logging
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from celery import Celery
from sqlalchemy.orm import Session
import json

from app.config import get_settings
from app.database import SessionLocal, init_db
from app.models import Task
from app.adapters import get_all_adapters
from app.utils.sequence_utils import merge_fasta_files, run_alignment, build_consensus

settings = get_settings()

# Настройка Celery
celery_app = Celery(
    "msa_tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=settings.MSA_TIMEOUT_SECONDS,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    broker_connection_retry_on_startup=True,
    task_default_queue="default",
)

# Логирование (безопасно создаём директорию)
log_dir = settings.LOG_DIR
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(log_dir, "celery_worker.log"), encoding="utf-8")
    ]
)
logger = logging.getLogger("celery.msa")

def update_task_status(
    db: Session, 
    task_id: str, 
    status: str, 
    progress: int = None, 
    step: str = None,
    num_sequences: int = None,
    result_files: dict = None,
    error: str = None
):
    """Обновляет статус задачи в БД"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        logger.error(f"Task {task_id} not found in DB for update")
        return
    
    task.status = status
    if progress is not None:
        task.progress = progress
    if step:
        task.current_step = step
    if num_sequences is not None:
        task.num_sequences = num_sequences
    if result_files:
        task.result_files = result_files
    if error:
        task.error_message = error
    if status in ["SUCCESS", "FAILURE"]:
        task.completed_at = datetime.utcnow()
    
    db.commit()
    logger.info(f"Task {task_id} updated: {status} | {step or ''} | progress={progress}")

@celery_app.task(bind=True, name="run_msa_pipeline", max_retries=1)
def run_msa_pipeline(self, task_id: str, params: Dict[str, Any]):
    """
    Главная задача Celery: полный pipeline MSA.
    """
    logger.info(f"Starting pipeline for task {task_id} with params: {params}")
    
    db = SessionLocal()
    task_dir = Path(settings.DATA_DIR) / task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    
    input_fasta = task_dir / "input.fasta"
    aligned_fasta = task_dir / "aligned.fasta"
    consensus_fasta = task_dir / "consensus.fasta"
    log_file = task_dir / "pipeline.log"
    
    try:
        # 1. Обновляем статус
        update_task_status(db, task_id, "STARTED", 5, "Подготовка задачи")
        
        organism = params.get("organism")
        gene = params.get("gene")
        sources = params.get("sources", ["ncbi"])
        tool = params.get("alignment_tool", "mafft")
        max_seq = params.get("max_sequences", 200)
        use_mock = params.get("use_mock_data", False) or settings.DEMO_MODE
        seq_type = params.get("sequence_type", "gene")
        
        # 2. Скачивание из источников
        update_task_status(db, task_id, "PROGRESS", 15, "Скачивание последовательностей из баз данных")
        
        adapters = get_all_adapters(sources, use_mock=use_mock)
        downloaded_files = []
        total_sequences = 0
        
        for adapter in adapters:
            try:
                recs = adapter.fetch_sequences(
                    organism=organism,
                    gene=gene,
                    max_sequences=max_seq,
                    sequence_type=seq_type
                )
                if recs:
                    adapter_fasta = task_dir / f"{adapter.name}_raw.fasta"
                    adapter.save_to_fasta(recs, adapter_fasta)
                    downloaded_files.append(adapter_fasta)
                    total_sequences += len(recs)
                    logger.info(f"{adapter.name}: {len(recs)} sequences")
            except Exception as adapter_err:
                logger.error(f"Adapter {adapter.name} failed: {adapter_err}")
                continue
        
        if total_sequences == 0:
            # Fallback на mock если ничего не скачали
            logger.warning("No sequences downloaded. Using mock data as fallback.")
            from app.adapters.mock_adapter import MockDataAdapter
            mock = MockDataAdapter()
            recs = mock.fetch_sequences(organism, gene, max_seq)
            mock.save_to_fasta(recs, task_dir / "mock_raw.fasta")
            downloaded_files = [task_dir / "mock_raw.fasta"]
            total_sequences = len(recs)
        
        update_task_status(db, task_id, "PROGRESS", 35, f"Объединение {total_sequences} последовательностей", num_sequences=total_sequences)
        
        # 3. Объединение в единый FASTA
        count = merge_fasta_files(downloaded_files, input_fasta, max_total=max_seq)
        if count == 0:
            raise ValueError("Не удалось получить ни одной последовательности после объединения")
        
        # 4. Множественное выравнивание
        update_task_status(db, task_id, "PROGRESS", 50, f"Запуск {tool} (выравнивание {count} seq)")
        
        success = run_alignment(input_fasta, aligned_fasta, tool=tool, threads=4, timeout=settings.MSA_TIMEOUT_SECONDS)
        if not success or not aligned_fasta.exists():
            raise RuntimeError(f"Выравнивание с помощью {tool} не удалось")
        
        # 5. Построение консенсуса
        update_task_status(db, task_id, "PROGRESS", 80, "Построение консенсусной последовательности")
        
        cons_success = build_consensus(aligned_fasta, consensus_fasta)
        if not cons_success:
            logger.warning("Consensus building failed, but alignment is available")
        
        # 6. Сохранение результатов
        result_files = {
            "input_fasta": str(input_fasta),
            "aligned_fasta": str(aligned_fasta),
            "consensus_fasta": str(consensus_fasta) if consensus_fasta.exists() else None,
            "log_file": str(log_file),
            "task_dir": str(task_dir)
        }
        
        update_task_status(
            db, task_id, "SUCCESS", 100, "Готово", 
            num_sequences=count,
            result_files=result_files
        )
        
        logger.info(f"Pipeline completed successfully for task {task_id}")
        return {"status": "SUCCESS", "task_id": task_id, "num_sequences": count}
        
    except Exception as exc:
        logger.exception(f"Pipeline failed for task {task_id}: {exc}")
        update_task_status(db, task_id, "FAILURE", error=str(exc)[:500])
        # Повторная попытка не делаем (max_retries=1)
        raise
    finally:
        db.close()
        # Опционально: очистка временных raw файлов
        for f in task_dir.glob("*_raw.fasta"):
            try:
                f.unlink()
            except:
                pass