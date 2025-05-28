import requests
from bs4 import BeautifulSoup
from urllib.parse import urlencode
import time
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from src.app.utils.constants import BASE_URL_VITIBRASIL
from .config import SCRAPING_CONFIG, NUMERIC_KEYWORDS, UNIT_PATTERNS
from .utils import normalize_text, parse_numeric_value, extract_year_range
from .exceptions import PageNotFoundError, TableNotFoundError

logger = logging.getLogger(__name__)

@dataclass
class SubOption:
    """Representa uma subopção de scraping"""
    code: str
    name: str

@dataclass
class PageMetadata:
    """Metadados de uma página de scraping"""
    min_year: Optional[int]
    max_year: Optional[int]
    sub_options: List[SubOption]
    display_name: str

@dataclass
class ScrapedData:
    """Dados raspados de uma página"""
    year: int
    option_name: str
    sub_option_name: Optional[str]
    data: List[Dict[str, Any]]

class BaseScraper:
    """Classe base para scraping do Vitibrasil"""
    
    def __init__(self):
        self.base_url = BASE_URL_VITIBRASIL
        self.config = SCRAPING_CONFIG
    
    def get_page_soup(self, url: str, description: str = "page") -> Optional[BeautifulSoup]:
        """
        Busca e parseia uma página, retornando objeto BeautifulSoup.
        
        Args:
            url: URL da página
            description: Descrição para logs
            
        Returns:
            BeautifulSoup object ou None se falhar
            
        Raises:
            PageNotFoundError: Se não conseguir carregar a página após tentativas
        """
        for attempt in range(1, self.config.MAX_RETRIES + 1):
            try:
                resp = requests.get(url, timeout=self.config.TIMEOUT)
                resp.raise_for_status()
                return BeautifulSoup(resp.content, 'lxml')
            except requests.exceptions.RequestException as e:
                logger.warning(f"Tentativa {attempt}/{self.config.MAX_RETRIES} falhou para {description}: {e}")
                if attempt == self.config.MAX_RETRIES:
                    raise PageNotFoundError(f"Não foi possível carregar {description} após {self.config.MAX_RETRIES} tentativas")
                time.sleep(2 * attempt)
        
        return None
    
    def get_page_metadata(self, option_code: str, reference_year: Optional[int] = None) -> PageMetadata:
        """
        Obtém metadados de uma página de opção.
        
        Args:
            option_code: Código da opção (ex: 'opt_02')
            reference_year: Ano de referência para buscar metadados
            
        Returns:
            PageMetadata com informações da página
        """
        if reference_year is None:
            reference_year = self.config.DEFAULT_REFERENCE_YEAR
        
        url = self._build_url({'ano': reference_year, 'opcao': option_code})
        soup = self.get_page_soup(url, f"metadata for {option_code}")
        
        if not soup:
            return PageMetadata(None, None, [], normalize_text(option_code) or option_code)
        
        # Extrai nome da opção
        display_name = self._extract_option_display_name(soup, option_code)
        
        # Extrai range de anos
        min_year, max_year = self._extract_year_range(soup)
        
        # Extrai subopções
        sub_options = self._extract_sub_options(soup)
        
        # Se não encontrou anos e há subopções, tenta com primeira subopção
        if (min_year is None or max_year is None) and sub_options:
            min_year, max_year = self._try_get_years_from_suboption(
                option_code, sub_options[0].code, reference_year
            )
        
        return PageMetadata(min_year, max_year, sub_options, display_name)
    
    def scrape_data_from_page(
        self, 
        year: int, 
        option_code: str, 
        suboption_code: Optional[str] = None,
        option_display_name: Optional[str] = None,
        suboption_display_name: Optional[str] = None
    ) -> ScrapedData:
        """
        Raspa dados de uma página específica.
        
        Args:
            year: Ano dos dados
            option_code: Código da opção
            suboption_code: Código da subopção (opcional)
            option_display_name: Nome de exibição da opção
            suboption_display_name: Nome de exibição da subopção
            
        Returns:
            ScrapedData com os dados extraídos
        """
        params = {'ano': year, 'opcao': option_code}
        if suboption_code:
            params['subopcao'] = suboption_code
        
        url = self._build_url(params)
        description = self._build_page_description(option_code, suboption_code, year)
        
        soup = self.get_page_soup(url, description)
        
        final_option_name = option_display_name or normalize_text(option_code) or option_code
        final_suboption_name = suboption_display_name
        
        if not soup:
            logger.warning(f"Falha ao carregar dados de {url}")
            return ScrapedData(year, final_option_name, final_suboption_name, [])
        
        # Extrai dados da tabela
        table_data = self._extract_table_data(soup, url, option_code)
        
        return ScrapedData(year, final_option_name, final_suboption_name, table_data)
    
    def _build_url(self, params: Dict[str, Any]) -> str:
        """Constrói URL com parâmetros"""
        return self.base_url + urlencode(params)
    
    def _build_page_description(self, option_code: str, suboption_code: Optional[str], year: int) -> str:
        """Constrói descrição da página para logs"""
        desc = f"data for {option_code}"
        if suboption_code:
            desc += f"/{suboption_code}"
        desc += f" year {year}"
        return desc
    
    def _extract_option_display_name(self, soup: BeautifulSoup, option_code: str) -> str:
        """Extrai nome de exibição da opção principal"""
        # Tenta botão da opção
        main_opt_button = soup.find('button', {'name': 'opcao', 'value': option_code})
        if main_opt_button and main_opt_button.get_text(strip=True):
            return normalize_text(main_opt_button.get_text(strip=True)) or option_code
        
        # Tenta título da página
        page_title_tag = soup.find('p', class_='text_center')
        if page_title_tag:
            title_text = page_title_tag.get_text(strip=True)
            if " - " in title_text:
                general_part = title_text.split(" - ")[0]
                return normalize_text(general_part.strip()) or option_code
            
            match_title = re.match(r"^(.*?)(?:\[\d{4}\])?$", title_text)
            if match_title and match_title.group(1).strip():
                return normalize_text(match_title.group(1).strip()) or option_code
        
        return normalize_text(option_code) or option_code
    
    def _extract_year_range(self, soup: BeautifulSoup) -> tuple[Optional[int], Optional[int]]:
        """Extrai range de anos da página"""
        year_label = soup.find('label', class_='lbl_pesq')
        if year_label and year_label.string:
            return extract_year_range(year_label.string)
        
        # Tenta no título da página
        page_center_text = soup.find('p', class_='text_center')
        if page_center_text and page_center_text.string:
            return extract_year_range(page_center_text.string)
        
        return None, None
    
    def _extract_sub_options(self, soup: BeautifulSoup) -> List[SubOption]:
        """Extrai subopções da página"""
        sub_options = []
        suboption_elements = soup.find_all(['button', 'input'], attrs={'name': 'subopcao'})
        
        for element in suboption_elements:
            if element.name == 'input' and element.get('type') != 'submit':
                continue
            
            sub_code = element.get('value')
            sub_name_text = (
                element.get_text(strip=True) if element.name == 'button' 
                else element.get('value')
            )
            
            if sub_code and sub_name_text:
                normalized_name = normalize_text(sub_name_text)
                if normalized_name:
                    sub_options.append(SubOption(sub_code, normalized_name))
        
        return sub_options
    
    def _try_get_years_from_suboption(
        self, 
        option_code: str, 
        suboption_code: str, 
        reference_year: int
    ) -> tuple[Optional[int], Optional[int]]:
        """Tenta obter anos usando uma subopção"""
        try:
            url = self._build_url({
                'ano': reference_year, 
                'opcao': option_code, 
                'subopcao': suboption_code
            })
            soup = self.get_page_soup(url, f"metadata for {option_code} with suboption")
            if soup:
                return self._extract_year_range(soup)
        except Exception as e:
            logger.warning(f"Erro ao tentar obter anos da subopção: {e}")
        
        return None, None
    
    def _extract_table_data(self, soup: BeautifulSoup, url: str, option_code: str) -> List[Dict[str, Any]]:
        """Extrai dados da tabela principal"""
        # Encontra tabela
        table = soup.select_one("table.tb_dados")
        if not table:
            table = soup.find(lambda tag: tag.name == "table" and "tb_dados" in (tag.get('class') or []))
        
        if not table:
            logger.info(f"Tabela de dados não encontrada em {url}")
            return []
        
        # Extrai cabeçalhos
        headers = self._extract_table_headers(table, url)
        if not headers:
            return []
        
        # Extrai dados das linhas
        return self._extract_table_rows(table, headers, option_code)
    
    def _extract_table_headers(self, table: BeautifulSoup, url: str) -> List[str]:
        """Extrai cabeçalhos da tabela"""
        # Tenta encontrar cabeçalhos no thead
        header_row = table.select_one("thead tr")
        if header_row:
            header_cells = header_row.find_all(['th', 'td'])
        else:
            # Procura na primeira linha com th ou strong
            all_rows = table.find_all('tr')
            header_cells = []
            
            for row in all_rows:
                potential_headers = row.find_all(['th', 'td'])
                if any(cell.name == 'th' for cell in potential_headers) or row.find('strong'):
                    header_cells = potential_headers
                    break
            
            # Fallback: primeira linha
            if not header_cells and all_rows:
                header_cells = all_rows[0].find_all(['th', 'td'])
        
        # Normaliza cabeçalhos
        headers = [normalize_text(cell.get_text(strip=True)) for cell in header_cells]
        headers = [h for h in headers if h]
        
        # Se não conseguiu extrair cabeçalhos, cria genéricos
        if not headers:
            logger.info(f"Não foi possível extrair cabeçalhos de {url}, usando genéricos")
            # Conta colunas da primeira linha de dados
            body = table.find('tbody')
            rows = body.find_all('tr') if body else table.find_all('tr')[1:]
            
            if rows:
                first_data_cols = rows[0].find_all('td')
                if first_data_cols:
                    headers = [f"coluna_{i+1}" for i in range(len(first_data_cols))]
                else:
                    headers = ["coluna_1", "coluna_2"]
            else:
                headers = ["coluna_1", "coluna_2"]
        
        return headers
    
    def _extract_table_rows(self, table: BeautifulSoup, headers: List[str], option_code: str) -> List[Dict[str, Any]]:
        """Extrai dados das linhas da tabela"""
        data = []
        contextual_category = None
        
        # Encontra linhas de dados
        body = table.find('tbody')
        rows = body.find_all('tr') if body else table.find_all('tr')[1:]
        
        for row in rows:
            cols = row.find_all('td')
            
            # Pula linhas sem colunas ou apenas com th
            if not cols:
                continue
            
            # Verifica se é linha de categoria
            if self._is_category_row(cols, option_code):
                text_content = cols[0].get_text(strip=True)
                if text_content and not text_content.lower().startswith(("total", "subtotal")):
                    contextual_category = text_content
                continue
            
            # Pula linhas de total/subtotal
            if self._is_total_row(cols):
                continue
            
            # Pula linhas com poucas colunas
            if len(cols) < min(len(headers), 2):
                continue
            
            # Extrai dados da linha
            row_data = self._extract_row_data(cols, headers, option_code)
            if row_data:
                row_data["categoria_tabela"] = contextual_category
                data.append(row_data)
                
                # Atualiza categoria contextual se necessário
                if option_code in ("opt_02", "opt_04") and self._is_first_col_tb_item(cols):
                    new_context = cols[0].get_text(strip=True)
                    if new_context and not new_context.lower().startswith("total"):
                        contextual_category = new_context
        
        return data
    
    def _is_category_row(self, cols: List, option_code: str) -> bool:
        """Verifica se linha é de categoria"""
        if len(cols) == 1 and (cols[0].has_attr('colspan') or cols[0].find('strong')):
            return True
        
        if (option_code == "opt_03" and len(cols) >= 2 and 
            'tb_item' in cols[0].get('class', []) and 'tb_item' in cols[1].get('class', [])):
            return True
        
        return False
    
    def _is_total_row(self, cols: List) -> bool:
        """Verifica se linha é de total/subtotal"""
        if not cols:
            return False
        
        first_cell_text = cols[0].get_text(strip=True).lower()
        return first_cell_text.startswith(("total", "subtotal"))
    
    def _is_first_col_tb_item(self, cols: List) -> bool:
        """Verifica se primeira coluna tem classe tb_item"""
        return len(cols) > 0 and 'tb_item' in cols[0].get('class', [])
    
    def _extract_row_data(self, cols: List, headers: List[str], option_code: str) -> Optional[Dict[str, Any]]:
        """Extrai dados de uma linha"""
        row_data = {}
        
        for i, cell in enumerate(cols):
            if i >= len(headers):
                break
            
            header = headers[i]
            value_str = cell.get_text(strip=True)
            
            # Determina se deve tentar conversão numérica
            is_numeric = self._should_convert_to_numeric(header, i, headers, option_code)
            
            # Converte valor
            if is_numeric:
                cleaned_value = parse_numeric_value(value_str)
                if cleaned_value is None and value_str not in ['-', '']:
                    cleaned_value = value_str  # Mantém string se não conseguir converter
            else:
                cleaned_value = value_str if value_str not in ['-', ''] else None
            
            # Processa chaves com unidades
            self._process_header_with_units(header, cleaned_value, row_data)
        
        # Retorna apenas se tem dados válidos
        return row_data if any(v is not None for v in row_data.values()) else None
    
    def _should_convert_to_numeric(self, header: str, index: int, headers: List[str], option_code: str) -> bool:
        """Determina se um valor deve ser convertido para numérico"""
        # Verifica palavras-chave no header
        if any(keyword in header for keyword in NUMERIC_KEYWORDS):
            return True
        
        # Última coluna geralmente é numérica
        if len(headers) > 1 and index == len(headers) - 1:
            return True
        
        # Regras específicas para certas opções
        if option_code in ("opt_05", "opt_06"):
            if (len(headers) > 1 and header == headers[1]) or \
               (len(headers) > 2 and header == headers[2]):
                return True
        
        return False
    
    def _process_header_with_units(self, header: str, value: Any, row_data: Dict[str, Any]) -> None:
        """Processa header que pode ter unidades embutidas"""
        import re
        
        # Formato com duplo underscore: quantidade__kg
        if "__" in header:
            parts = header.split("__", 1)
            base_name, unit = parts[0], parts[1]
            row_data[base_name] = value
            row_data[f"unidade_{base_name}"] = unit
        
        # Formato com sufixo de unidade: quantidade_kg
        elif re.match(r"^(.*)_(" + "|".join(UNIT_PATTERNS) + r")$", header):
            match = re.match(r"^(.*)_(" + "|".join(UNIT_PATTERNS) + r")$", header)
            base_name, unit = match.group(1), match.group(2)
            row_data[base_name] = value
            row_data[f"unidade_{base_name}"] = unit
        
        else:
            row_data[header] = value