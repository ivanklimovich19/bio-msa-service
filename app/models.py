from sqlalchemy import Column, String, Integer, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base
import uuid

def generate_uuid():
    return str(uuid.uuid4())

class Task(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, default=generate_uuid)
    organism = Column(String(255), nullable=False, index=True)
    gene = Column(String(255), nullable=True)
    sources = Column(JSON, nullable=False)  # ["ncbi", "ensembl"]
    alignment_tool = Column(String(50), nullable=False)  # mafft | clustalo | muscle
    params = Column(JSON, nullable=True)  # max_sequences, use_mock и т.д.
    
    status = Column(String(20), default="PENDING", index=True)  # PENDING, STARTED, PROGRESS, SUCCESS, FAILURE
    progress = Column(Integer, default=0)
    current_step = Column(String(100), default="Инициализация")
    
    result_files = Column(JSON, nullable=True)  # {"input.fasta": "...", "aligned.fasta": path, "consensus.fasta": path, "log.txt": path}
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Кол-во скачанных последовательностей
    num_sequences = Column(Integer, default=0)

    def to_dict(self):
        return {
            "task_id": self.id,
            "organism": self.organism,
            "gene": self.gene,
            "sources": self.sources,
            "alignment_tool": self.alignment_tool,
            "status": self.status,
            "progress": self.progress,
            "current_step": self.current_step,
            "num_sequences": self.num_sequences,
            "result_files": self.result_files,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }