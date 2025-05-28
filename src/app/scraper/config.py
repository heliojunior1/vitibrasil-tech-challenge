# src/app/scraper/config.py
from typing import Dict, List, Tuple
from dataclasses import dataclass

@dataclass
class ScrapingConfig:
    """Configurações para scraping"""
    DEFAULT_REFERENCE_YEAR: int = 2023
    FALLBACK_MIN_YEAR: int = 2023
    FALLBACK_MAX_YEAR: int = 2023
    REQUEST_DELAY: float = 0.5
    MAX_RETRIES: int = 3
    TIMEOUT: Tuple[int, int] = (30, 60)

SCRAPING_CONFIG = ScrapingConfig()

# Mapeamento de opções para códigos
OPCOES_MAPPING: Dict[str, str] = {
    "producao": "opt_02",
    "processamento": "opt_03", 
    "comercializacao": "opt_04",
    "importacao": "opt_05",
    "exportacao": "opt_06"
}

# Códigos principais para scraping completo
MAIN_OPTIONS_TO_SCRAPE: List[str] = ["opt_02", "opt_03", "opt_04", "opt_05", "opt_06"]

# Palavras-chave para identificação de dados numéricos
NUMERIC_KEYWORDS: List[str] = ['quantidade', 'valor', 'kg', 'us', 'l', '_ano', 'coluna_2']

# Unidades de medida reconhecidas
UNIT_PATTERNS: List[str] = ['kg', 'l', 'us', 'ml', 'hl', 'ton', 'g', 'm3']

