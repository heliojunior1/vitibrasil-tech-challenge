# src/app/scraper/partial_scraper.py
import logging
from typing import List, Optional
from .base_scraper import BaseScraper, ScrapedData
from .config import OPCOES_MAPPING, SCRAPING_CONFIG
from .exceptions import InvalidOptionError, YearRangeError

logger = logging.getLogger(__name__)

class PartialScraper(BaseScraper):
    """Scraper para coleta parcial de dados por parâmetros específicos"""
    
    def scrape_by_params(self, ano_min: int, ano_max: int, opcao_nome: str) -> List[dict]:
        """
        Executa scraping por parâmetros específicos.
        
        Args:
            ano_min: Ano mínimo
            ano_max: Ano máximo  
            opcao_nome: Nome da opção ('producao', 'comercializacao', etc.)
            
        Returns:
            Lista de dicionários com dados raspados
            
        Raises:
            InvalidOptionError: Se opção for inválida
            YearRangeError: Se range de anos for inválido
        """
        self._validate_params(ano_min, ano_max, opcao_nome)
        
        option_code = OPCOES_MAPPING[opcao_nome]
        logger.info(f"Raspando {opcao_nome} ({option_code}) de {ano_min} a {ano_max}")
        
        # Obtém metadados da opção
        metadata = self.get_page_metadata(option_code, ano_max)
        
        scraped_data = []
        
        for year in range(ano_min, ano_max + 1):
            if not metadata.sub_options:
                # Sem subopções
                data = self._scrape_year_safely(
                    year, option_code, None, 
                    metadata.display_name, None
                )
                if data:
                    scraped_data.append(data)
            else:
                # Com subopções
                for sub_option in metadata.sub_options:
                    data = self._scrape_year_safely(
                        year, option_code, sub_option.code,
                        metadata.display_name, sub_option.name
                    )
                    if data:
                        scraped_data.append(data)
        
        logger.info(f"Coleta concluída: {len(scraped_data)} conjuntos de dados")
        return self._convert_to_dict_format(scraped_data)
    
    def _validate_params(self, ano_min: int, ano_max: int, opcao_nome: str) -> None:
        """Valida parâmetros de entrada"""
        if opcao_nome not in OPCOES_MAPPING:
            raise InvalidOptionError(
                f"Opção '{opcao_nome}' inválida. "
                f"Opções disponíveis: {list(OPCOES_MAPPING.keys())}"
            )
        
        current_year = 2023  # Pode ser obtido dinamicamente
        if not (1970 <= ano_min <= current_year and 1970 <= ano_max <= current_year):
            raise YearRangeError(f"Anos devem estar entre 1970 e {current_year}")
        
        if ano_min > ano_max:
            raise YearRangeError("Ano mínimo deve ser menor ou igual ao ano máximo")
    
    def _scrape_year_safely(
        self, 
        year: int, 
        option_code: str, 
        suboption_code: Optional[str],
        option_name: str,
        suboption_name: Optional[str]
    ) -> Optional[ScrapedData]:
        """Raspa dados de um ano com tratamento de erro"""
        try:
            data = self.scrape_data_from_page(
                year, option_code, suboption_code, option_name, suboption_name
            )
            
            if data and data.data:
                return data
            else:
                logger.info(f"Nenhum dado encontrado para {option_code}/{suboption_code} ano {year}")
                return None
                
        except Exception as e:
            logger.warning(f"Erro ao raspar {option_code}/{suboption_code} ano {year}: {e}")
            return None
    
    def _convert_to_dict_format(self, scraped_data: List[ScrapedData]) -> List[dict]:
        """Converte ScrapedData para formato de dicionário legado"""
        return [
            {
                "ano": data.year,
                "aba": data.option_name, 
                "subopcao": data.sub_option_name,
                "dados": data.data
            }
            for data in scraped_data
        ]

# Função de compatibilidade
def run_scrape_by_params(ano_min: int, ano_max: int, opcao_nome: str) -> List[dict]:
    """
    Função de compatibilidade com a interface anterior.
    
    Args:
        ano_min: Ano mínimo
        ano_max: Ano máximo
        opcao_nome: Nome da opção
        
    Returns:
        Lista de dicionários com dados raspados
    """
    scraper = PartialScraper()
    return scraper.scrape_by_params(ano_min, ano_max, opcao_nome)