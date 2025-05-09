import requests
from bs4 import BeautifulSoup
from urllib.parse import urlencode
import time
import json
import unicodedata
import re

def normalize_text(text):
    """Normalizes text by removing accents, converting to lowercase, and replacing spaces/hyphens with underscores."""
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
            # print(f"Fetching {description} from {url} (Attempt {attempt}/{max_retries})")
            resp = requests.get(url, timeout=(30, 60))
            resp.raise_for_status()
            return BeautifulSoup(resp.content, 'lxml')
        except requests.exceptions.RequestException as e:
            print(f"Error fetching {description} at {url}: {e}")
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
        print(f"Could not fetch metadata page for {option_code} at year {reference_year}")
        return None, None, [], normalize_text(option_code) # Fallback display name

    min_year, max_year = None, None
    main_option_display_name = normalize_text(option_code) # Fallback

    # Try to get main option display name from its button
    # This requires a page where main option buttons are visible, typically the initial page for the option.
    main_opt_button = soup.find('button', {'name': 'opcao', 'value': option_code})
    if main_opt_button and main_opt_button.get_text(strip=True):
        main_option_display_name = normalize_text(main_opt_button.get_text(strip=True))
    else:
        # Fallback: Try to get from page title <p class="text_center">
        page_title_tag = soup.find('p', class_='text_center')
        if page_title_tag:
            title_text = page_title_tag.get_text(strip=True)
            # If title is like "Main Category - SubCategory [Year]" or "Main Category [Year]"
            # Extract the "Main Category" part.
            if " - " in title_text: # "Processamento - Viniferas [2023]"
                general_part = title_text.split(" - ")[0]
                main_option_display_name = normalize_text(general_part.strip())
            else: # "Comercializacao [2023]"
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
    # Suboption buttons can be <button> or <input type="submit">
    suboption_elements = soup.find_all(['button', 'input'], attrs={'name': 'subopcao'})

    for btn in suboption_elements:
        if btn.name == 'input' and btn.get('type') != 'submit':
            continue # Skip if it's an input but not a submit button for suboption

        sub_code = btn.get('value')
        sub_name_text = btn.get_text(strip=True) if btn.name == 'button' else btn.get('value') # Input submit often has text in value
        
        # For input type="submit", the text might be in its 'id' or a label associated with it.
        # A common pattern is that the button text itself is descriptive.
        if btn.name == 'input' and btn.get('type') == 'submit':
            # The value attribute of input type=submit is often the displayed text
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
                          # These are the descriptive names to be used in the JSON output
                          json_aba_name: str = None,
                          json_subopcao_name: str = None):
    base_url = "http://vitibrasil.cnpuv.embrapa.br/index.php?"
    params = {'ano': year, 'opcao': option_code}
    if suboption_code:
        params['subopcao'] = suboption_code
    
    url = base_url + urlencode(params)
    # Use option_code and suboption_code for logging the fetch attempt
    page_description = f"data for {option_code}"
    if suboption_code:
        page_description += f"/{suboption_code}"
    page_description += f" year {year}"

    soup = get_page_soup(url, description=page_description)

    # Determine final names for JSON output
    final_aba_name = json_aba_name if json_aba_name else normalize_text(option_code)
    final_subopcao_name = json_subopcao_name # This will be the descriptive normalized name or None

    if not soup:
        print(f"Falha ao carregar dados de {url}")
        return {"ano": year, "aba": final_aba_name, "subopcao": final_subopcao_name, "dados": []}

    tabela_bs = soup.select_one("table.tb_dados")
    if not tabela_bs:
        tabela_bs = soup.find(lambda tag: tag.name == "table" and "tb_dados" in (tag.get('class') or []))
    
    if not tabela_bs:
        print(f"Tabela de dados não encontrada em {url}")
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
        
        for r_idx, r in enumerate(all_table_rows_for_header):
            potential_headers = r.find_all(['th', 'td'])
            if any(ph.name == 'th' for ph in potential_headers) or r.find('strong'):
                header_cells_elements = potential_headers
                start_index_for_rows = r_idx + 1
                break
        if not header_cells_elements and all_table_rows_for_header: 
            header_cells_elements = all_table_rows_for_header[0].find_all(['th', 'td'])
            start_index_for_rows = 1
    
    header_keys = [normalize_text(cell.get_text(strip=True)) for cell in header_cells_elements]
    header_keys = [hk for hk in header_keys if hk]

    if not header_keys:
        print(f"Alerta: Não foi possível extrair nomes de cabeçalho da tabela em {url}")
        first_data_row_cols = 0
        body_for_col_count = tabela_bs.find('tbody')
        rows_for_col_count = body_for_col_count.find_all('tr') if body_for_col_count else tabela_bs.find_all('tr')[start_index_for_rows:]
        if rows_for_col_count:
            first_data_row_cols_elements = rows_for_col_count[0].find_all('td')
            if first_data_row_cols_elements : first_data_row_cols = len(first_data_row_cols_elements)
        
        if first_data_row_cols > 0:
            header_keys = [f"coluna_{i+1}" for i in range(first_data_row_cols)]
        else: 
            header_keys = ["coluna_1", "coluna_2"] 
        print(f"Usando cabeçalhos genéricos: {header_keys}")

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
        
        # Ensure we have enough columns for the detected headers, or at least 2 for basic data.
        # This helps avoid errors if a row is malformed or not a data row.
        if len(cols) < len(header_keys) and len(cols) < 2:
            continue


        for i, cell_element in enumerate(cols):
            if i < len(header_keys): # Process only as many cells as we have header keys
                original_key = header_keys[i] # Use original_key for decisions
                value_str = cell_element.get_text(strip=True)
                
                cleaned_value = None
                if value_str == '-' or value_str == '':
                    cleaned_value = None 
                else:
                    # Determine if the value should be numeric based on the original_key
                    is_numeric_candidate = any(k_word in original_key for k_word in ['quantidade', 'valor', 'kg', 'us', 'l', '_ano', 'coluna_2']) or \
                                           (len(header_keys) > 1 and i == len(header_keys) -1) # last column often numeric
                    
                    # For import/export, the second and third columns are often Quantidade and Valor US$
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
                
                # Handle splitting of the key if it contains "__"
                if "__" in original_key:
                    parts = original_key.split("__", 1)
                    base_name = parts[0]  # e.g., "quantidade"
                    unit = parts[1]       # e.g., "kg"
                    
                    current_row_data[base_name] = cleaned_value # Store the (potentially numeric) value
                    current_row_data[f"unidade_{base_name}"] = unit # Store the unit, e.g., "unidade_quantidade"
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

if __name__ == '__main__':
    MAIN_OPTIONS_TO_SCRAPE = ["opt_02", "opt_03", "opt_04", "opt_05", "opt_06"]
    # For testing:
    # MAIN_OPTIONS_TO_SCRAPE = ["opt_03"] # Test Processamento
    # MAIN_OPTIONS_TO_SCRAPE = ["opt_04"] # Test Comercializacao
    # MAIN_OPTIONS_TO_SCRAPE = ["opt_05"] # Test Importacao
    # MAIN_OPTIONS_TO_SCRAPE = ["opt_06"] # Test Exportacao

    all_scraped_data = []
    DEFAULT_YEAR_FOR_METADATA_DISCOVERY = 2023 
    FALLBACK_MIN_YEAR = 2023
    FALLBACK_MAX_YEAR = 2023 

    for opt_code in MAIN_OPTIONS_TO_SCRAPE:
        print(f"\n>>> Processing Main Option Code: {opt_code} <<<")
        
        min_year_meta, max_year_meta, sub_options_list, main_opt_display_name = get_page_metadata(opt_code, DEFAULT_YEAR_FOR_METADATA_DISCOVERY)
        
        print(f"Descriptive name for {opt_code}: {main_opt_display_name}")

        current_min_year = 2023 
        current_max_year = max_year_meta if max_year_meta is not None else FALLBACK_MAX_YEAR
        
        # Override for testing specific year/option
        # current_min_year = 2023
        # current_max_year = 2023
        # if opt_code == "opt_05":
        #     current_min_year = 2023
        #     current_max_year = 2023


        print(f"Scraping {opt_code} ({main_opt_display_name}) for years: {current_min_year} to {current_max_year}")
        if sub_options_list:
            print(f"Found suboptions: {[(s['code'], s['name']) for s in sub_options_list]}")
        else:
            print(f"No suboptions found for {opt_code} ({main_opt_display_name}).")

        for year_to_scrape in range(current_min_year, current_max_year + 1):
            if not sub_options_list:
                print(f"\n--- Scraping: {opt_code} ({main_opt_display_name}) | Ano: {year_to_scrape} ---")
                time.sleep(0.5) 
                scraped_data_item = get_data_from_embrapa(year_to_scrape, opt_code, None,
                                                          json_aba_name=main_opt_display_name,
                                                          json_subopcao_name=None)
                if scraped_data_item and scraped_data_item.get("dados"):
                    all_scraped_data.append(scraped_data_item)
                elif scraped_data_item:
                    print(f"No data rows found for {opt_code} ({main_opt_display_name}) for year {year_to_scrape}")
            else:
                for sub_opt_detail in sub_options_list:
                    # Test specific suboption:
                    # if opt_code == "opt_03" and sub_opt_detail['code'] != "subopt_01": continue
                    # if opt_code == "opt_05" and sub_opt_detail['code'] != "subopt_01": continue


                    print(f"\n--- Scraping: {opt_code}/{sub_opt_detail['code']} ({main_opt_display_name}/{sub_opt_detail['name']}) | Ano: {year_to_scrape} ---")
                    time.sleep(0.5) 
                    scraped_data_item = get_data_from_embrapa(year_to_scrape, opt_code, sub_opt_detail['code'],
                                                              json_aba_name=main_opt_display_name,
                                                              json_subopcao_name=sub_opt_detail['name'])
                    if scraped_data_item and scraped_data_item.get("dados"):
                        all_scraped_data.append(scraped_data_item)
                    elif scraped_data_item:
                        print(f"No data rows for {opt_code}/{sub_opt_detail['code']} ({main_opt_display_name}/{sub_opt_detail['name']}) for year {year_to_scrape}")
    
    total_entries = len(all_scraped_data)
    total_individual_records = sum(len(item.get('dados', [])) for item in all_scraped_data)

    print(f"\n\nProcessamento Concluído.")
    print(f"Total de combinações (ano/aba/subopção) com dados: {total_entries}")
    print(f"Total de registros individuais de dados (linhas de tabela): {total_individual_records}")

    if all_scraped_data:
        actual_min_year_scraped = min((item['ano'] for item in all_scraped_data if item.get('ano') is not None), default=FALLBACK_MIN_YEAR)
        actual_max_year_scraped = max((item['ano'] for item in all_scraped_data if item.get('ano') is not None), default=FALLBACK_MAX_YEAR)
        
        file_out_name = f"dados_embrapa_vitibrasil_{actual_min_year_scraped}_a_{actual_max_year_scraped}_descritivo.json"
        with open(file_out_name, 'w', encoding='utf-8') as f:
            json.dump(all_scraped_data, f, ensure_ascii=False, indent=2)
        print(f"Dados salvos em: {file_out_name}")
    else:
        print("Nenhum dado foi coletado.")