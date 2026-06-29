from app.adapters.base import BaseDataAdapter, SequenceRecord
from typing import List, Optional

class EBIAdapter(BaseDataAdapter):
    """Заглушка для EBI dbfetch / ENA"""
    
    def __init__(self):
        super().__init__("ebi")

    def fetch_sequences(
        self, 
        organism: str, 
        gene: Optional[str] = None, 
        max_sequences: int = 100,
        sequence_type: str = "gene"
    ) -> List[SequenceRecord]:
        self.logger.warning("EBI dbfetch adapter not fully implemented yet. Returning empty list.")
        # TODO: Использовать https://www.ebi.ac.uk/Tools/dbfetch/
        return []