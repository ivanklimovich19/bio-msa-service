from app.adapters.base import BaseDataAdapter, SequenceRecord
from typing import List, Optional
import random
import hashlib

class MockDataAdapter(BaseDataAdapter):
    """
    Улучшенный Mock-адаптер для демонстрации.
    Генерирует разные последовательности для разных организмов и генов.
    """

    def __init__(self):
        super().__init__("mock")

    def _get_diverse_sequence(self, organism: str, gene: Optional[str], length: int = 480) -> str:
        """Генерирует разнообразную последовательность на основе organism + gene"""
        
        # Создаём уникальный seed на основе названия организма и гена
        seed_input = f"{organism.lower().strip()}_{ (gene or 'genome').lower().strip() }"
        seed = int(hashlib.md5(seed_input.encode()).hexdigest()[:12], 16)
        rng = random.Random(seed)
        
        bases = "ATGC"
        
        # Разный GC-контент в зависимости от "организма" (более реалистично)
        org_hash = hash(organism.lower()) % 100
        gc_content = 0.40 + (org_hash / 250)   # от ~40% до ~80%
        
        weights = [
            (1 - gc_content) / 2,   # A
            gc_content / 2,         # G
            gc_content / 2,         # C
            (1 - gc_content) / 2    # T
        ]
        
        # Генерируем базовую последовательность
        seq = ''.join(rng.choices(bases, weights=weights, k=length))
        
        # Добавляем вариацию между "штаммами" (5-12% мутаций)
        final_seq = ""
        for i, char in enumerate(seq):
            if rng.random() < 0.09:                    # 9% мутаций
                final_seq += rng.choice(bases)
            elif rng.random() < 0.025 and i > 10:      # небольшие делеции
                continue
            elif rng.random() < 0.015:                 # небольшие инсерции
                final_seq += rng.choice(bases) + char
            else:
                final_seq += char
        
        # Обрезаем/дополняем до нужной длины
        if len(final_seq) > length:
            final_seq = final_seq[:length]
        while len(final_seq) < length:
            final_seq += rng.choice(bases)
            
        return final_seq

    def fetch_sequences(
        self, 
        organism: str, 
        gene: Optional[str] = None, 
        max_sequences: int = 100,
        sequence_type: str = "gene"
    ) -> List[SequenceRecord]:
        
        self.logger.info(f"Mock fetch: {organism} | gene={gene} | max={max_sequences}")
        
        records = []
        gene_name = gene or "whole_genome"
        
        # Генерируем от 8 до 20 последовательностей
        num = min(max_sequences, max(8, min(20, max_sequences // 2 + 5)))
        
        for i in range(num):
            strain = f"strain_{chr(65 + (i % 26))}{i // 26 if i >= 26 else ''}"
            accession = f"MOCK{organism[:3].upper()}{i:04d}"
            
            # Каждый "штамм" получает немного другую последовательность
            seq_length = 460 + (i % 35)
            sequence = self._get_diverse_sequence(organism, gene, length=seq_length)
            
            rec = SequenceRecord(
                organism=organism,
                strain=strain,
                gene=gene_name,
                accession=accession,
                sequence=sequence,
                source="mock"
            )
            records.append(rec)
        
        return records