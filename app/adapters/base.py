from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class SequenceRecord:
    """Унифицированная запись последовательности"""
    def __init__(self, organism: str, strain: str, gene: str, accession: str, sequence: str, source: str):
        self.organism = organism
        self.strain = strain or "unknown"
        self.gene = gene or "unknown"
        self.accession = accession
        self.sequence = sequence
        self.source = source

    def to_fasta_header(self) -> str:
        return f">{self.organism}|{self.strain}|{self.gene}|{self.accession}|{self.source}"

    def to_fasta(self) -> str:
        return f"{self.to_fasta_header()}\n{self.sequence}\n"

class BaseDataAdapter(ABC):
    """Абстрактный базовый класс для всех адаптеров источников данных"""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"adapter.{name}")

    @abstractmethod
    def fetch_sequences(
        self, 
        organism: str, 
        gene: Optional[str] = None, 
        max_sequences: int = 100,
        sequence_type: str = "gene"
    ) -> List[SequenceRecord]:
        """
        Скачать/получить последовательности.
        Возвращает список SequenceRecord.
        """
        pass

    def standardize_header(self, record: SequenceRecord) -> str:
        """Гарантирует единый формат заголовка"""
        return record.to_fasta_header()

    def save_to_fasta(self, records: List[SequenceRecord], output_path: Path) -> int:
        """Сохраняет список записей в FASTA файл"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            for rec in records:
                f.write(rec.to_fasta())
        self.logger.info(f"Saved {len(records)} sequences to {output_path}")
        return len(records)