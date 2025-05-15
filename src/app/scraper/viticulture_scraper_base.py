import requests
from bs4 import BeautifulSoup
from urllib.parse import urlencode
import time
import json
import unicodedata
import re
import os
import logging
logger = logging.getLogger(__name__) 

CACHED_DATA_FILENAME = "vitibrasil_data_cache.json"

def normalize_text(text):
    if not text:
        return None
    text = str(text)
    nfkd_form = unicodedata.normalize('NFKD', text)
    only_ascii = nfkd_form.encode('ASCII', 'ignore').decode('utf-8')
    text_cleaned = re.sub(r'[^\w\s\(\)\$\€\,\.-]', '', only_ascii)
    text_cleaned = text_cleaned.replace('(Kg)', '_kg').replace('(US$)', '_us').replace('(L)', '_l')
    text_cleaned = re.sub(r'[^\w\s]', '', text_cleaned) 
    return text_cleaned.strip().lower().replace(" ", "_").replace("-", "_")

def get_page_soup(url, description="page"):
    """Fetches and parses a page, returns a BeautifulSoup object or None."""
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, timeout=(30, 60))
            resp.raise_for_status()
            return BeautifulSoup(resp.content, 'lxml')
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching {description} at {url}: {e}")
            if attempt == max_retries:
                return None
            time.sleep(2 * attempt)
    return None

def get_page_metadata(option_code, reference_year=2023):
    """
    Fetches metadata for a given option: year range, suboptions, and descriptive names.
    Returns (min_year, max_year, list_of_suboption_details, main_option_display_name).
    Each suboption_detail is a dict: {'code': 'subopt_XX', 'name': 'Normalized Display Name'}
    """
    base_url = "http://vitibrasil.cnpuv.embrapa.br/index.php?"
    meta_url_params = {'ano': reference_year, 'opcao': option_code}
    soup = get_page_soup(base_url + urlencode(meta_url_params), description=f"metadata for {option_code}")

    if not soup:
        logger.info(f"Could not fetch metadata page for {option_code} at year {reference_year}")
        return None, None, [], normalize_text(option_code) # Fallback display name

    min_year, max_year = None, None
    main_option_display_name = normalize_text(option_code) # Fallback

    main_opt_button = soup.find('button', {'name': 'opcao', 'value': option_code})
    if main_opt_button and main_opt_button.get_text(strip=True):
        main_option_display_name = normalize_text(main_opt_button.get_text(strip=True))
    else:
        page_title_tag = soup.find('p', class_='text_center')
        if page_title_tag:
            title_text = page_title_tag.get_text(strip=True)
            if " - " in title_text: 
                general_part = title_text.split(" - ")[0]
                main_option_display_name = normalize_text(general_part.strip())
            else: 
                match_title = re.match(r"^(.*?)(?:\[\d{4}\])?$", title_text)
                if match_title and match_title.group(1).strip():
                    main_option_display_name = normalize_text(match_title.group(1).strip())

    year_label = soup.find('label', class_='lbl_pesq')
    if year_label and year_label.string:
        match_year_range = re.search(r'\[(\d{4})-(\d{4})\]', year_label.string)
        if match_year_range:
            min_year = int(match_year_range.group(1))
            max_year = int(match_year_range.group(2))

    sub_options_details = []
    suboption_elements = soup.find_all(['button', 'input'], attrs={'name': 'subopcao'})

    for btn in suboption_elements:
        if btn.name == 'input' and btn.get('type') != 'submit':
            continue

        sub_code = btn.get('value')
        sub_name_text = btn.get_text(strip=True) if btn.name == 'button' else btn.get('value')
        
        if btn.name == 'input' and btn.get('type') == 'submit':
             sub_name_text = btn.get('value')

        if sub_code and sub_name_text:
            sub_options_details.append({'code': sub_code, 'name': normalize_text(sub_name_text)})
            
    if (min_year is None or max_year is None) and sub_options_details:
        meta_url_params_with_sub = {'ano': reference_year, 'opcao': option_code, 'subopcao': sub_options_details[0]['code']}
        soup_with_sub = get_page_soup(base_url + urlencode(meta_url_params_with_sub), description=f"metadata for {option_code} with suboption")
        if soup_with_sub:
            year_label_sub = soup_with_sub.find('label', class_='lbl_pesq')
            if year_label_sub and year_label_sub.string:
                match_sub = re.search(r'\[(\d{4})-(\d{4})\]', year_label_sub.string)
                if match_sub:
                    min_year = int(match_sub.group(1))
                    max_year = int(match_sub.group(2))
    
    if soup and (min_year is None or max_year is None):
        page_center_text_for_year = soup.find('p', class_='text_center')
        if page_center_text_for_year and page_center_text_for_year.string:
            match_title_year = re.search(r'\[(\d{4})\]', page_center_text_for_year.string)
            if match_title_year:
                year_from_title = int(match_title_year.group(1))
                min_year = min_year or year_from_title 
                max_year = max_year or year_from_title

    return min_year, max_year, sub_options_details, main_option_display_name


def get_data_from_embrapa(year: int, option_code: str, suboption_code: str = None,
                          json_aba_name: str = None,
                          json_subopcao_name: str = None):
    base_url = "http://vitibrasil.cnpuv.embrapa.br/index.php?"
    params = {'ano': year, 'opcao': option_code}
    if suboption_code:
        params['subopcao'] = suboption_code
    
    url = base_url + urlencode(params)
    page_description = f"data for {option_code}"
    if suboption_code:
        page_description += f"/{suboption_code}"
    page_description += f" year {year}"

    soup = get_page_soup(url, description=page_description)

    final_aba_name = json_aba_name if json_aba_name else normalize_text(option_code)
    final_subopcao_name = json_subopcao_name

    if not soup:
        logger.info(f"Falha ao carregar dados de {url}")
        return {"ano": year, "aba": final_aba_name, "subopcao": final_subopcao_name, "dados": []}

    tabela_bs = soup.select_one("table.tb_dados")
    if not tabela_bs:
        tabela_bs = soup.find(lambda tag: tag.name == "table" and "tb_dados" in (tag.get('class') or []))
    
    if not tabela_bs:
        logger.info(f"Tabela de dados não encontrada em {url}")
        return {"ano": year, "aba": final_aba_name, "subopcao": final_subopcao_name, "dados": []}

    header_cells_elements = []
    start_index_for_rows = 0 

    header_row_thead = tabela_bs.select_one("thead tr")
    if header_row_thead:
        header_cells_elements = header_row_thead.find_all(['th', 'td'])
    else: 
        all_table_rows_for_header = tabela_bs.find_all('tr')
        if not all_table_rows_for_header:
            return {"ano": year, "aba": final_aba_name, "subopcao": final_subopcao_name, "dados": []}
        
        for r_idx, r_loop in enumerate(all_table_rows_for_header):
            potential_headers = r_loop.find_all(['th', 'td'])
            if any(ph.name == 'th' for ph in potential_headers) or r_loop.find('strong'):
                header_cells_elements = potential_headers
                start_index_for_rows = r_idx + 1
                break
        if not header_cells_elements and all_table_rows_for_header: 
            header_cells_elements = all_table_rows_for_header[0].find_all(['th', 'td'])
            start_index_for_rows = 1
    
    header_keys = [normalize_text(cell.get_text(strip=True)) for cell in header_cells_elements]
    header_keys = [hk for hk in header_keys if hk]

    if not header_keys:
        logger.info(f"Alerta: Não foi possível extrair nomes de cabeçalho da tabela em {url}")
        first_data_row_cols = 0
        body_for_col_count = tabela_bs.find('tbody')
        rows_for_col_count = body_for_col_count.find_all('tr') if body_for_col_count else tabela_bs.find_all('tr')[start_index_for_rows:]
        if rows_for_col_count:
            first_data_row_cols_elements = rows_for_col_count[0].find_all('td')
            if first_data_row_cols_elements: first_data_row_cols = len(first_data_row_cols_elements)
        
        if first_data_row_cols > 0:
            header_keys = [f"coluna_{i+1}" for i in range(first_data_row_cols)]
        else: 
            header_keys = ["coluna_1", "coluna_2"] 
        logger.info(f"Usando cabeçalhos genéricos: {header_keys}")

    dados_coletados = []
    categoria_contextual = None 

    body = tabela_bs.find('tbody')
    rows_to_parse = body.find_all('tr') if body else tabela_bs.find_all('tr')[start_index_for_rows:]

    for row in rows_to_parse:
        cols = row.find_all('td')

        if not cols: 
            if row.find_all('th'): continue 
            continue

        if (len(cols) == 1 and (cols[0].has_attr('colspan') or cols[0].find('strong'))) or \
           (option_code == "opt_03" and len(cols) >= 2 and 'tb_item' in cols[0].get('class', []) and 'tb_item' in cols[1].get('class', [])):
            
            text_content = cols[0].get_text(strip=True)
            if text_content and not text_content.lower().startswith("total") and not text_content.lower().startswith("subtotal"):
                categoria_contextual = text_content 
            continue 

        current_row_data = {}
        is_first_col_tb_item = False
        if len(cols) > 0 and 'tb_item' in cols[0].get('class', []):
            is_first_col_tb_item = True
        
        first_cell_text_lower = cols[0].get_text(strip=True).lower() if len(cols) > 0 else ""
        if first_cell_text_lower.startswith("total") or first_cell_text_lower.startswith("subtotal"):
            continue
        
        if len(cols) < len(header_keys) and len(cols) < 2:
            continue

        for i, cell_element in enumerate(cols):
            if i < len(header_keys): 
                original_key = header_keys[i] 
                value_str = cell_element.get_text(strip=True)
                
                cleaned_value = None
                if value_str == '-' or value_str == '':
                    cleaned_value = None 
                else:
                    is_numeric_candidate = any(k_word in original_key for k_word in ['quantidade', 'valor', 'kg', 'us', 'l', '_ano', 'coluna_2']) or \
                                           (len(header_keys) > 1 and i == len(header_keys) -1) 
                    
                    if option_code in ("opt_05", "opt_06") and \
                       ((len(header_keys) > 1 and original_key == header_keys[1]) or \
                        (len(header_keys) > 2 and original_key == header_keys[2])):
                        is_numeric_candidate = True

                    if is_numeric_candidate:
                        try:
                            val_clean_num = value_str.replace('.', '').replace(',', '.')
                            cleaned_value = float(val_clean_num)
                        except ValueError:
                            cleaned_value = value_str 
                    else:
                        cleaned_value = value_str
                
                if "__" in original_key:
                    parts = original_key.split("__", 1)
                    base_name = parts[0] 
                    unit = parts[1]      
                    current_row_data[base_name] = cleaned_value 
                    current_row_data[f"unidade_{base_name}"] = unit 
                elif re.match(r"^(.*)_(kg|l|us|ml|hl|ton|g|m3)$", original_key):
                    match = re.match(r"^(.*)_(kg|l|us|ml|hl|ton|g|m3)$", original_key)
                    base_name = match.group(1)
                    unit = match.group(2)
                    current_row_data[base_name] = cleaned_value
                    current_row_data[f"unidade_{base_name}"] = unit
                else:
                    current_row_data[original_key] = cleaned_value
        
        if not current_row_data or not any(v is not None for v in current_row_data.values()):
            continue

        current_row_data["categoria_tabela"] = categoria_contextual 

        if option_code in ("opt_02", "opt_04"):
            if is_first_col_tb_item and len(cols) > 0:
                 new_context_candidate = cols[0].get_text(strip=True)
                 if new_context_candidate and not new_context_candidate.lower().startswith("total"):
                    categoria_contextual = new_context_candidate
        dados_coletados.append(current_row_data)
    
    return {
        "ano": year,
        "aba": final_aba_name,
        "subopcao": final_subopcao_name,
        "dados": dados_coletados
    }