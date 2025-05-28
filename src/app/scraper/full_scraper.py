# src/app/scraper/full_scraper.py
import logging
from typing import List, Optional
from .base_scraper import BaseScraper, ScrapedData
from .config import MAIN_OPTIONS_TO_SCRAPE, SCRAPING_CONFIG
from .exceptions import ScrapingError

logger = logging.getLogger(__name__)

class FullScraper(BaseScraper):
    """Scraper para coleta completa de dados de todas as opções"""
    
    def scrape_all_data(self, output_filepath: Optional[str] = None) -> List[dict]:
        """
        Executa scraping completo de todas as opções e anos disponíveis.
        
        Args:
            output_filepath: Caminho para salvar dados em JSON (opcional)
            
        Returns:
            Lista de dicionários com dados raspados
        """
        all_scraped_data = []
        
        for option_code in MAIN_OPTIONS_TO_SCRAPE:
            logger.info(f"Processando opção: {option_code}")
            
            try:
                option_data = self._scrape_option_data(option_code)
                all_scraped_data.extend(option_data)
                
            except ScrapingError as e:
                logger.error(f"Erro ao processar opção {option_code}: {e}")
                continue
            except Exception as e:
                logger.error(f"Erro inesperado ao processar opção {option_code}: {e}")
                continue
        
        self._log_summary(all_scraped_data)
        
        if output_filepath and all_scraped_data:
            self._save_to_file(all_scraped_data, output_filepath)
        
        return self._convert_to_dict_format(all_scraped_data)
    
    def _scrape_option_data(self, option_code: str) -> List[ScrapedData]:
        """Raspa dados de uma opção específica"""
        metadata = self.get_page_metadata(option_code)
        
        min_year = metadata.min_year or SCRAPING_CONFIG.FALLBACK_MIN_YEAR
        max_year = metadata.max_year or SCRAPING_CONFIG.FALLBACK_MAX_YEAR
        
        logger.info(f"Opção {option_code} ({metadata.display_name}): anos {min_year}-{max_year}")
        
        if metadata.sub_options:
            logger.info(f"Subopções encontradas: {[(s.code, s.name) for s in metadata.sub_options]}")
        
        option_data = []
        
        for year in range(min_year, max_year + 1):
            if not metadata.sub_options:
                # Sem subopções
                data = self._scrape_year_data(year, option_code, None, metadata.display_name, None)
                if data and data.data:
                    option_data.append(data)
            else:
                # Com subopções
                for sub_option in metadata.sub_options:
                    data = self._scrape_year_data(
                        year, option_code, sub_option.code, 
                        metadata.display_name, sub_option.name
                    )
                    if data and data.data:
                        option_data.append(data)
        
        return option_data
    
    def _scrape_year_data(
        self, 
        year: int, 
        option_code: str, 
        suboption_code: Optional[str],
        option_name: str,
        suboption_name: Optional[str]
    ) -> Optional[ScrapedData]:
        """Raspa dados de um ano específico com delay"""
        import time
        
        logger.info(f"Raspando: {option_code}/{suboption_code or 'main'} - Ano {year}")
        
        try:
            time.sleep(SCRAPING_CONFIG.REQUEST_DELAY)
            return self.scrape_data_from_page(
                year, option_code, suboption_code, option_name, suboption_name
            )
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
    
    def _save_to_file(self, data: List[ScrapedData], filepath: str) -> None:
        """Salva dados em arquivo JSON"""
        import json
        import os
        
        try:
            output_dir = os.path.dirname(filepath)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
            
            dict_data = self._convert_to_dict_format(data)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(dict_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Dados salvos em: {filepath}")
        except Exception as e:
            logger.error(f"Erro ao salvar arquivo {filepath}: {e}")
    
    def _log_summary(self, data: List[ScrapedData]) -> None:
        """Log do resumo da coleta"""
        total_entries = len(data)
        total_records = sum(len(item.data) for item in data)
        
        logger.info(f"Processamento concluído:")
        logger.info(f"- Total de combinações (ano/aba/subopção): {total_entries}")
        logger.info(f"- Total de registros individuais: {total_records}")

# Função de compatibilidade
def run_full_scrape(output_filepath: Optional[str] = None) -> List[dict]:
    """
    Função de compatibilidade com a interface anterior.
    
    Args:
        output_filepath: Caminho para salvar arquivo JSON
        
    Returns:
        Lista de dicionários com dados raspados
    """
    scraper = FullScraper()
    return scraper.scrape_all_data(output_filepath)