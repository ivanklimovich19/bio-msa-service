from pathlib import Path
from typing import List, Tuple
from Bio import SeqIO, AlignIO
from Bio.Align import AlignInfo
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
import logging
import subprocess
import shutil
import os

logger = logging.getLogger(__name__)

def merge_fasta_files(input_files: List[Path], output_file: Path, max_total: int = 5000) -> int:
    """
    Объединяет несколько FASTA в один с уникальными заголовками.
    Возвращает общее кол-во последовательностей.
    """
    output_file.parent.mkdir(parents=True, exist_ok=True)
    seen_accessions = set()
    count = 0
    
    with open(output_file, "w", encoding="utf-8") as out_f:
        for fasta_path in input_files:
            if not fasta_path.exists():
                continue
            for record in SeqIO.parse(str(fasta_path), "fasta"):
                if count >= max_total:
                    logger.warning(f"Reached max_sequences limit ({max_total})")
                    break
                # Уникальность по accession + organism
                key = f"{record.id}_{record.description[:50]}"
                if key in seen_accessions:
                    continue
                seen_accessions.add(key)
                
                # Перезаписываем заголовок в стандартный формат если нужно
                SeqIO.write(record, out_f, "fasta")
                count += 1
            if count >= max_total:
                break
    
    logger.info(f"Merged {count} sequences into {output_file}")
    return count

def run_alignment(
    input_fasta: Path, 
    output_aligned: Path, 
    tool: str = "mafft",
    threads: int = 4,
    timeout: int = 3600 * 3
) -> bool:
    """
    Запускает инструмент множественного выравнивания.
    Поддерживает mafft, clustalo, muscle.
    """
    input_fasta = Path(input_fasta)
    output_aligned = Path(output_aligned)
    output_aligned.parent.mkdir(parents=True, exist_ok=True)
    
    if not input_fasta.exists() or input_fasta.stat().st_size == 0:
        logger.error("Input FASTA is empty or missing")
        return False
    
    cmd = []
    env = os.environ.copy()
    
    if tool == "mafft":
        # MAFFT --auto хорошо работает для большинства случаев, включая много seq
        cmd = [
            "mafft", 
            "--auto", 
            "--thread", str(threads),
            "--quiet",
            str(input_fasta)
        ]
        # MAFFT пишет alignment в stdout
        try:
            with open(output_aligned, "w") as out:
                result = subprocess.run(
                    cmd, 
                    stdout=out, 
                    stderr=subprocess.PIPE, 
                    text=True, 
                    timeout=timeout,
                    env=env
                )
            if result.returncode != 0:
                logger.error(f"MAFFT failed: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            logger.error("MAFFT timed out")
            return False
            
    elif tool == "clustalo":
        cmd = [
            "clustalo",
            "-i", str(input_fasta),
            "-o", str(output_aligned),
            "--outfmt=fasta",
            "--threads", str(threads),
            "--force"
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
            if result.returncode != 0:
                logger.error(f"Clustal Omega failed: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            logger.error("Clustal Omega timed out")
            return False
            
    elif tool == "muscle":
        cmd = [
            "muscle",
            "-align", str(input_fasta),
            "-output", str(output_aligned),
            "-threads", str(threads)
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
            if result.returncode != 0:
                logger.error(f"MUSCLE failed: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            logger.error("MUSCLE timed out")
            return False
    else:
        logger.error(f"Unknown alignment tool: {tool}")
        return False
    
    if output_aligned.exists() and output_aligned.stat().st_size > 0:
        logger.info(f"Alignment completed with {tool}: {output_aligned}")
        return True
    return False

def build_consensus(
    aligned_fasta: Path, 
    output_consensus: Path,
    threshold: float = 0.51
) -> bool:
    """
    Строит консенсусную последовательность на основе выравнивания.
    Использует majority vote (dumb_consensus).
    """
    try:
        alignment = AlignIO.read(str(aligned_fasta), "fasta")
        if len(alignment) == 0:
            logger.error("Empty alignment")
            return False
        
        summary = AlignInfo.SummaryInfo(alignment)
        # dumb_consensus — простой majority consensus
        consensus_seq = summary.dumb_consensus(threshold=threshold, ambiguous="N")
        
        consensus_record = SeqRecord(
            Seq(str(consensus_seq)),
            id="consensus",
            description=f"Consensus from {len(alignment)} sequences | tool=Bio.Align | threshold={threshold}"
        )
        
        output_consensus.parent.mkdir(parents=True, exist_ok=True)
        SeqIO.write(consensus_record, str(output_consensus), "fasta")
        
        logger.info(f"Consensus built and saved to {output_consensus}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to build consensus: {e}")
        return False

def get_alignment_stats(aligned_fasta: Path) -> dict:
    """Простая статистика выравнивания"""
    try:
        alignment = AlignIO.read(str(aligned_fasta), "fasta")
        return {
            "num_sequences": len(alignment),
            "alignment_length": alignment.get_alignment_length(),
            "average_identity": None  # Можно добавить расчёт при необходимости
        }
    except Exception:
        return {"num_sequences": 0, "alignment_length": 0}