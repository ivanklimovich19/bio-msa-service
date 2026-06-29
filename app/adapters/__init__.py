from app.adapters.base import BaseDataAdapter, SequenceRecord
from app.adapters.mock_adapter import MockDataAdapter
from app.adapters.ncbi_adapter import NCBIAdapter
from app.adapters.ensembl_adapter import EnsemblAdapter
from app.adapters.ebi_adapter import EBIAdapter
from typing import List, Dict, Type
import logging

logger = logging.getLogger(__name__)

ADAPTER_REGISTRY: Dict[str, Type[BaseDataAdapter]] = {
    "ncbi": NCBIAdapter,
    "ensembl": EnsemblAdapter,
    "ebi": EBIAdapter,
    "mock": MockDataAdapter,
}

def get_adapter(source: str) -> BaseDataAdapter:
    """Фабрика адаптеров"""
    source = source.lower()
    if source == "mock":
        return MockDataAdapter()
    adapter_class = ADAPTER_REGISTRY.get(source)
    if not adapter_class:
        logger.warning(f"Unknown source '{source}', falling back to NCBI")
        return NCBIAdapter()
    return adapter_class()

def get_all_adapters(sources: List[str], use_mock: bool = False) -> List[BaseDataAdapter]:
    """Возвращает список инициализированных адаптеров"""
    adapters = []
    for src in sources:
        if use_mock:
            adapters.append(MockDataAdapter())
        else:
            adapters.append(get_adapter(src))
    return adapters