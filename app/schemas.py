from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from enum import Enum

class AlignmentTool(str, Enum):
    MAFFT = "mafft"
    CLUSTALO = "clustalo"
    MUSCLE = "muscle"

class DataSource(str, Enum):
    NCBI = "ncbi"
    ENSEMBL = "ensembl"
    EBI = "ebi"

class MSARequest(BaseModel):
    organism: str = Field(..., min_length=3, max_length=200, description="Таксон, например: 'Escherichia coli' или 'Homo sapiens'")
    gene: Optional[str] = Field(None, max_length=100, description="Название гена (опционально). Если None — попытка скачать геномы")
    sources: List[DataSource] = Field(default=[DataSource.NCBI], description="Список источников данных")
    alignment_tool: AlignmentTool = Field(default=AlignmentTool.MAFFT)
    max_sequences: int = Field(default=200, ge=1, le=5000, description="Максимальное кол-во последовательностей (ограничено для демо)")
    use_mock_data: bool = Field(default=False, description="Использовать mock-данные (для тестов без интернета/API)")
    sequence_type: str = Field(default="gene", description="'gene' или 'genome' (genome — только для небольших вирусов/бактерий)")

    @validator('organism')
    def validate_organism(cls, v):
        import re
        if not re.match(r'^[A-Za-z0-9\s\.\-\(\)]+$', v):
            raise ValueError("Название организма может содержать только буквы, цифры, пробелы, точки, дефисы и скобки")
        return v.strip()

    @validator('gene')
    def validate_gene(cls, v):
        if v is None:
            return v
        import re
        if not re.match(r'^[A-Za-z0-9\s\.\-\_]+$', v):
            raise ValueError("Название гена может содержать только буквы, цифры, пробелы, ., -, _")
        return v.strip()

class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    progress: int
    current_step: str
    num_sequences: int
    result_files: Optional[Dict[str, str]] = None
    error_message: Optional[str] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None

class TaskCreateResponse(BaseModel):
    task_id: str
    status: str = "PENDING"
    message: str = "Задача создана и поставлена в очередь. Используйте /status/{task_id} для отслеживания."