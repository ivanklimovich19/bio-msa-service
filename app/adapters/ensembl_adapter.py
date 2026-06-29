from app.adapters.base import BaseDataAdapter, SequenceRecord
from typing import List, Optional

class EnsemblAdapter(BaseDataAdapter):
    """Заглушка для Ensembl REST API (реализуйте при необходимости)"""
    
    def __init__(self):
        super().__init__("ensembl")

    def fetch_sequences(
        self, 
        organism: str, 
        gene: Optional[str] = None, 
        max_sequences: int = 100,
        sequence_type: str = "gene"
    ) -> List[SequenceRecord]:
        self.logger.warning("Ensembl adapter not fully implemented yet. Returning empty list.")
        # TODO: Реализовать через https://rest.ensembl.org/
        # Пример: lookup символа гена, затем sequence/id
        return []