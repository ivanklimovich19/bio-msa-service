from app.adapters.base import BaseDataAdapter, SequenceRecord
from typing import List, Optional
from Bio import Entrez, SeqIO
from io import StringIO
import time
import logging
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

Entrez.email = settings.NCBI_EMAIL
if settings.NCBI_API_KEY:
    Entrez.api_key = settings.NCBI_API_KEY

class NCBIAdapter(BaseDataAdapter):
    """
    Адаптер для NCBI (GenBank / RefSeq).
    Использует Biopython Entrez E-utilities.
    Для больших объёмов рекомендуется NCBI Datasets CLI (см. Dockerfile).
    """
    
    def __init__(self):
        super().__init__("ncbi")

    def fetch_sequences(
        self, 
        organism: str, 
        gene: Optional[str] = None, 
        max_sequences: int = 100,
        sequence_type: str = "gene"
    ) -> List[SequenceRecord]:
        
        self.logger.info(f"NCBI fetch: organism='{organism}', gene='{gene}', max={max_sequences}")
        
        records = []
        
        try:
            # Строим поисковый запрос
            if gene:
                # Улучшенный запрос для генов
                query = f'"{organism}"[Organism] AND "{gene}"[Gene] AND RefSeq[Filter]'
            else:
                # Для целых геномов
                query = f'"{organism}"[Organism] AND (complete genome[Title] OR chromosome complete[Title]) AND RefSeq[Filter]'
            
            self.logger.debug(f"Entrez esearch query: {query}")
            
            # Поиск
            handle = Entrez.esearch(db="nucleotide", term=query, retmax=min(max_sequences, 500), sort="relevance")
            search_results = Entrez.read(handle)
            handle.close()
            
            id_list = search_results.get("IdList", [])
            self.logger.info(f"Found {len(id_list)} accessions in NCBI")
            
            if not id_list:
                return records
            
            # Получаем записи батчами по 20 (ограничение E-utilities)
            batch_size = 20
            for i in range(0, min(len(id_list), max_sequences), batch_size):
                batch = id_list[i:i + batch_size]
                
                try:
                    handle = Entrez.efetch(db="nucleotide", id=batch, rettype="fasta", retmode="text")
                    fasta_data = handle.read()
                    handle.close()
                    
                    # Парсим FASTA
                    fasta_io = StringIO(fasta_data)
                    for seq_record in SeqIO.parse(fasta_io, "fasta"):
                        # Пытаемся извлечь метаданные из описания
                        desc = seq_record.description
                        strain = "unknown"
                        gene_name = gene or "unknown"
                        
                        # Простой парсинг описания (можно улучшить regex)
                        if "[" in desc and "]" in desc:
                            try:
                                org_part = desc.split("[")[1].split("]")[0]
                                if org_part != organism:
                                    organism = org_part  # обновляем если точнее
                            except:
                                pass
                        
                        rec = SequenceRecord(
                            organism=organism,
                            strain=strain,
                            gene=gene_name,
                            accession=seq_record.id,
                            sequence=str(seq_record.seq),
                            source="ncbi"
                        )
                        records.append(rec)
                        
                        if len(records) >= max_sequences:
                            break
                    
                    time.sleep(0.4)  # Уважение к rate limit NCBI (3 req/sec без ключа)
                    
                except Exception as batch_err:
                    self.logger.warning(f"Batch error for {batch}: {batch_err}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"NCBI Entrez error: {e}")
            # Не падаем — возвращаем что удалось скачать
        
        self.logger.info(f"NCBI adapter returned {len(records)} sequences")
        return records[:max_sequences]