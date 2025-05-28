# src/app/scraper/utils.py
import unicodedata
import re
from typing import Optional

def normalize_text(text: Optional[str]) -> Optional[str]:
    """
    Normaliza texto removendo acentos e caracteres especiais.
    
    Args:
        text: Texto a ser normalizado
        
    Returns:
        Texto normalizado ou None se input for None/vazio
    """
    if not text:
        return None
    
    text = str(text)
    # Remove acentos
    nfkd_form = unicodedata.normalize('NFKD', text)
    only_ascii = nfkd_form.encode('ASCII', 'ignore').decode('utf-8')
    
    # Remove caracteres especiais, mantendo alguns símbolos importantes
    text_cleaned = re.sub(r'[^\w\s\(\)\$\€\,\.-]', '', only_ascii)
    
    # Substitui padrões específicos
    replacements = {
        '(Kg)': '_kg',
        '(US$)': '_us', 
        '(L)': '_l'
    }
    
    for old, new in replacements.items():
        text_cleaned = text_cleaned.replace(old, new)
    
    # Remove caracteres restantes e normaliza espaços
    text_cleaned = re.sub(r'[^\w\s]', '', text_cleaned)
    return text_cleaned.strip().lower().replace(" ", "_").replace("-", "_")

def parse_numeric_value(value_str: str) -> Optional[float]:
    """
    Converte string em valor numérico, tratando formatação brasileira.
    
    Args:
        value_str: String a ser convertida
        
    Returns:
        Valor float ou None se não for conversível
    """
    if not value_str or value_str in ['-', '']:
        return None
    
    try:
        # Formato brasileiro: 1.234.567,89 -> 1234567.89
        val_clean = value_str.replace('.', '').replace(',', '.')
        return float(val_clean)
    except ValueError:
        return None

def extract_year_range(text: str) -> tuple[Optional[int], Optional[int]]:
    """
    Extrai range de anos de um texto no formato [YYYY-YYYY] ou [YYYY].
    
    Args:
        text: Texto contendo informação de anos
        
    Returns:
        Tupla (ano_min, ano_max) ou (None, None) se não encontrar
    """
    # Procura por range: [2020-2023]
    range_match = re.search(r'\[(\d{4})-(\d{4})\]', text)
    if range_match:
        return int(range_match.group(1)), int(range_match.group(2))
    
    # Procura por ano único: [2023]
    single_match = re.search(r'\[(\d{4})\]', text)
    if single_match:
        year = int(single_match.group(1))
        return year, year
    
    return None, None