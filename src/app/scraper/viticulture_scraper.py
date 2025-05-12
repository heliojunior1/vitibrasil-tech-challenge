import requests
from bs4 import BeautifulSoup
from urllib.parse import urlencode
import time
import json
import unicodedata
import re
import os
import logging
from typing import List, Optional, Dict, Any, Tuple


logger = logging.getLogger(__name__)

# URL base para as requisições
BASE_URL = "http://vitibrasil.cnpuv.embrapa.br/index.php"

# Mapeamento de códigos de opção para nomes de abas (normalizados)
# Estes são os nomes que esperamos após a normalização.
# A função get_page_metadata irá descobrir os nomes reais e normalizá-los.
# Esta lista é mais para referência e para a função run_filtered_scrape.
ALL_KNOWN_OPTIONS = ["opt_01", "opt_02", "opt_03", "opt_04", "opt_05", "opt_06"]
# opt_01: Resumo (geralmente não tem sub-opções com tabelas de dados anuais)
# opt_02: Produção
# opt_03: Processamento
# opt_04: Comercialização
# opt_05: Importação
# opt_06: Exportação

# --- Funções Auxiliares ---

def normalize_text(text: str) -> str:
    """Normaliza o texto: minúsculas, remove acentos, substitui espaços e hífens por underscore."""
    if not text:
        return ""
    # Remove acentos
    nfkd_form = unicodedata.normalize('NFKD', text)
    text_sem_acentos = "".join([c for c in nfkd_form if not unicodedata.combining(c)])
    # Substitui espaços e hífens por underscore e converte para minúsculas
    text_normalizado = re.sub(r'[\s-]+', '_', text_sem_acentos).lower()
    return text_normalizado

def make_request(payload: dict) -> Optional[BeautifulSoup]:
    """Faz uma requisição POST para a URL base com o payload fornecido."""
    try:
        response = requests.post(BASE_URL, data=payload, timeout=20) # Aumentado timeout
        response.raise_for_status()  # Levanta exceção para erros HTTP
        return BeautifulSoup(response.content, 'lxml') # Usar lxml para melhor performance
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro na requisição para {BASE_URL} com payload {payload}: {e}")
        return None
    except Exception as e_gen:
        logger.error(f"Erro inesperado ao processar requisição para {BASE_URL}: {e_gen}")
        return None


def get_page_metadata(opt_value: str, year_for_suboptions: int) -> Tuple[Optional[int], Optional[int], List[Dict[str, str]], Optional[str]]:
    """
    Obtém metadados da página: anos disponíveis, sub-opções e nome da aba principal.
    O 'year_for_suboptions' é usado para carregar a página e descobrir as sub-opções.
    """
    payload = {'ano': year_for_suboptions, opt_value: ''}
    soup = make_request(payload)
    if not soup:
        return None, None, [], None

    min_year, max_year = None, None
    year_select = soup.find('select', attrs={'onchange': 'submit()'}) # O select de ano
    if year_select:
        options = year_select.find_all('option')
        years = sorted([int(opt.get('value')) for opt in options if opt.get('value').isdigit()])
        if years:
            min_year = years[0]
            max_year = years[-1]

    sub_options_list = []
    # Tenta encontrar o nome da aba principal e as sub-opções
    # As sub-opções são tipicamente inputs do tipo 'submit' com name começando com 'subopt_'
    # e value contendo o nome da sub-opção.
    # O nome da aba principal é o 'value' do input 'submit' que tem o 'name' igual a opt_value
    main_opt_name_normalized = None
    
    forms = soup.find_all('form', attrs={'name': 'form'})
    for form in forms:
        # Encontrar o nome da aba principal
        main_opt_input = form.find('input', {'name': opt_value, 'type': 'submit'})
        if main_opt_input and main_opt_input.get('value'):
            main_opt_name_normalized = normalize_text(main_opt_input.get('value'))

        # Encontrar sub-opções
        sub_option_inputs = form.find_all('input', {'type': 'submit', 'name': lambda x: x and x.startswith('subopt_')})
        for sub_input in sub_option_inputs:
            sub_opt_name = sub_input.get('value')
            sub_opt_code = sub_input.get('name')
            if sub_opt_name and sub_opt_code:
                sub_options_list.append({
                    'name': normalize_text(sub_opt_name), # Normaliza o nome da sub-opção
                    'code': sub_opt_code
                })
    
    if not main_opt_name_normalized and opt_value == "opt_01": # Caso especial para "Resumo"
        main_opt_name_normalized = "resumo"


    logger.debug(f"Metadados para {opt_value} (ano {year_for_suboptions}): Anos [{min_year}-{max_year}], "
                 f"Aba Principal Normalizada: '{main_opt_name_normalized}', Sub-opções: {len(sub_options_list)}")
    return min_year, max_year, sub_options_list, main_opt_name_normalized


def get_data_from_embrapa(
    year: int,
    main_option_code: str,
    sub_option_code: Optional[str] = None,
    json_aba_name: Optional[str] = None, # Nome normalizado da aba principal para o JSON
    json_subopcao_name: Optional[str] = None # Nome normalizado da sub-opção para o JSON
) -> Optional[Dict[str, Any]]:
    """
    Busca dados de uma tabela específica da Embrapa para um ano, opção principal e, opcionalmente, sub-opção.
    Retorna um dicionário estruturado ou None em caso de falha.
    """
    payload = {'ano': year, main_option_code: ''}
    if sub_option_code:
        payload[sub_option_code] = '' # Adiciona a sub-opção ao payload se fornecida

    soup = make_request(payload)
    if not soup:
        logger.error(f"Falha ao obter soup para ano {year}, opção {main_option_code}, sub-opção {sub_option_code}")
        return None

    # Encontra todas as tabelas com a classe 'tb_base'
    tables = soup.find_all('table', class_='tb_base')
    if not tables:
        logger.info(f"Nenhuma tabela 'tb_base' encontrada para ano {year}, opção {main_option_code}, sub-opção {sub_option_code}.")
        # Retorna uma estrutura indicando que a página foi acessada mas sem dados tabulares
        return {
            "ano": year,
            "aba": json_aba_name or normalize_text(main_option_code), # Usa o nome normalizado fornecido ou normaliza o código
            "subopcao": json_subopcao_name if sub_option_code else None,
            "dados": [] # Lista vazia indica que não foram encontradas linhas de dados
        }

    table_data_list = []
    for table_index, table in enumerate(tables):
        headers = [normalize_text(th.text.strip()) for th in table.find_all('th', class_='tb_th')]
        if not headers: # Algumas tabelas podem não ter th, mas sim td.tb_cont na primeira linha como cabeçalho
            first_row_tds = table.find('tr').find_all('td', class_='tb_cont')
            if first_row_tds and len(first_row_tds) > 1: # Heurística: se tem múltiplos tds na primeira linha
                 headers = [normalize_text(td.text.strip()) for td in first_row_tds]

        if not headers:
            logger.warning(f"Cabeçalhos não encontrados para tabela {table_index} em {year}, {main_option_code}, {sub_option_code}")
            continue


        rows_data = []
        # Itera sobre as linhas da tabela, ignorando a primeira se for cabeçalho (já processado)
        # As linhas de dados geralmente têm a classe 'tr_dados_altcolor' ou 'tr_dados_color'
        data_rows = table.find_all('tr', class_=lambda x: x and ('tr_dados_altcolor' in x or 'tr_dados_color' in x))
        
        # Se não encontrou com classes específicas, tenta pegar todas as 'tr' e pular a primeira se for cabeçalho
        if not data_rows:
            all_rows = table.find_all('tr')
            if all_rows and headers: # Se temos cabeçalhos, pulamos a primeira linha
                data_rows = all_rows[1:]
            elif all_rows: # Sem cabeçalhos claros, pegamos todas as linhas
                data_rows = all_rows


        for row in data_rows:
            columns = row.find_all('td', class_='tb_cont')
            if len(columns) == len(headers): # Garante que o número de colunas corresponde aos cabeçalhos
                row_dict = {}
                # O primeiro header é 'produto' ou 'cultivar', o resto são 'ano_xxxx' ou 'quantidade'/'valor'
                # Para simplificar, vamos usar os headers normalizados como chaves
                for i, col in enumerate(columns):
                    header_key = headers[i]
                    # Tenta converter para float se for numérico, senão mantém como string
                    value_text = col.text.strip()
                    if value_text == '-': # Tratar hífen como nulo ou zero, dependendo da preferência. Aqui, como None.
                        row_dict[header_key] = None
                    else:
                        try:
                            # Remove pontos de milhar antes de converter para float
                            cleaned_value = value_text.replace('.', '').replace(',', '.')
                            row_dict[header_key] = float(cleaned_value)
                        except ValueError:
                            row_dict[header_key] = value_text # Mantém como string se não for conversível
                rows_data.append(row_dict)
            elif columns: # Log se o número de colunas não bate mas existem colunas
                 logger.warning(f"Número de colunas ({len(columns)}) não corresponde aos cabeçalhos ({len(headers)}) na tabela {table_index} para {year}, {main_option_code}, {sub_option_code}. Linha ignorada.")


        if rows_data: # Adiciona apenas se encontrou dados para esta tabela
            table_data_list.extend(rows_data) # Usar extend para mesclar listas de dicionários se houver múltiplas tabelas com os mesmos headers

    if not table_data_list:
        logger.info(f"Nenhum dado tabular processado para ano {year}, opção {main_option_code}, sub-opção {sub_option_code} apesar de tabelas 'tb_base' existirem.")

    return {
        "ano": year,
        "aba": json_aba_name or normalize_text(main_option_code),
        "subopcao": json_subopcao_name if sub_option_code else None,
        "dados": table_data_list
    }

# --- Funções de Raspagem Principais ---

def run_full_scrape(output_filepath: str = None) -> list:
    """
    Executa a raspagem completa de todos os dados de todas as opções e anos disponíveis.
    Salva os dados em um arquivo JSON se output_filepath for fornecido.
    Retorna uma lista de todos os dados raspados.
    """
    all_scraped_data = []
    # O ano padrão para descobrir metadados (sub-opções, etc.)
    # Usar um ano recente é geralmente uma boa ideia.
    DEFAULT_YEAR_FOR_METADATA_DISCOVERY = datetime.now().year - 1 # Ano anterior como padrão

    for opt_code in ALL_KNOWN_OPTIONS:
        logger.info(f"\n>>> Processando Opção Principal: {opt_code} <<<")
        
        # Obtém metadados para a opção principal (anos disponíveis, sub-opções)
        min_year, max_year, sub_options, main_opt_name_norm = get_page_metadata(opt_code, DEFAULT_YEAR_FOR_METADATA_DISCOVERY)

        if min_year is None or max_year is None:
            logger.warning(f"Não foi possível determinar o range de anos para a opção {opt_code}. Pulando.")
            continue
        
        if not main_opt_name_norm:
            logger.warning(f"Não foi possível determinar o nome normalizado da aba para {opt_code}. Pulando.")
            continue

        logger.info(f"Raspando dados para '{main_opt_name_norm}' (código: {opt_code}) de {min_year} a {max_year}")

        for year_to_scrape in range(min_year, max_year + 1):
            if not sub_options or opt_code == "opt_01": # opt_01 (Resumo) geralmente não tem sub-opções com tabelas de dados
                logger.info(f"\n--- Raspando: {main_opt_name_norm} | Ano: {year_to_scrape} ---")
                time.sleep(0.5) # Delay para não sobrecarregar o servidor
                scraped_data_item = get_data_from_embrapa(year_to_scrape, opt_code, None,
                                                          json_aba_name=main_opt_name_norm,
                                                          json_subopcao_name=None)
                if scraped_data_item and scraped_data_item.get("dados"):
                    all_scraped_data.append(scraped_data_item)
                elif scraped_data_item: # Item foi retornado mas sem dados (lista vazia)
                    logger.info(f"Nenhuma linha de dados encontrada para {main_opt_name_norm} no ano {year_to_scrape}")

            else: # Se existem sub-opções
                for sub_opt in sub_options:
                    sub_opt_code_val = sub_opt['code']
                    sub_opt_name_norm = sub_opt['name'] # Já está normalizado
                    logger.info(f"\n--- Raspando: {main_opt_name_norm} / {sub_opt_name_norm} | Ano: {year_to_scrape} ---")
                    time.sleep(0.5) # Delay
                    scraped_data_item = get_data_from_embrapa(year_to_scrape, opt_code, sub_opt_code_val,
                                                              json_aba_name=main_opt_name_norm,
                                                              json_subopcao_name=sub_opt_name_norm)
                    if scraped_data_item and scraped_data_item.get("dados"):
                        all_scraped_data.append(scraped_data_item)
                    elif scraped_data_item:
                        logger.info(f"Nenhuma linha de dados para {main_opt_name_norm}/{sub_opt_name_norm} no ano {year_to_scrape}")
    
    total_entries = len(all_scraped_data)
    total_individual_records = sum(len(item.get('dados', [])) for item in all_scraped_data)

    logger.info(f"\n\nProcessamento de Raspagem Completa Concluído.")
    logger.info(f"Total de combinações (ano/aba/subopção) com dados: {total_entries}")
    logger.info(f"Total de registros individuais de dados (linhas de tabela): {total_individual_records}")

    if all_scraped_data and output_filepath:
        try:
            output_dir = os.path.dirname(output_filepath)
            if output_dir and not os.path.exists(output_dir): # Cria o diretório se não existir
                os.makedirs(output_dir, exist_ok=True)
            with open(output_filepath, 'w', encoding='utf-8') as f:
                json.dump(all_scraped_data, f, ensure_ascii=False, indent=2)
            logger.info(f"Dados raspados também salvos em: {output_filepath}")
        except Exception as e:
            logger.error(f"Erro ao salvar arquivo JSON de cache em {output_filepath}: {e}")
    elif not all_scraped_data and output_filepath:
         logger.warning("Nenhum dado foi coletado para salvar no arquivo JSON.")
         
    return all_scraped_data


def run_filtered_scrape(
    target_categories_normalized: List[str],
    start_year_filter: int,
    end_year_filter: int,
    output_filepath: str = None
) -> list:
    """
    Executa a raspagem de dados para categorias e um intervalo de anos específicos.
    Salva os dados em um arquivo JSON se output_filepath for fornecido.
    Retorna uma lista dos dados raspados.
    """
    all_scraped_data = []
    # Use o ano final do filtro do usuário para descobrir metadados,
    # pois é mais provável que reflita as subopções atuais e os intervalos de anos disponíveis.
    DEFAULT_YEAR_FOR_METADATA_DISCOVERY = end_year_filter

    options_to_scrape_details = [] # Armazena detalhes das opções que correspondem às categorias do usuário

    logger.info(f"Tentando mapear categorias solicitadas: {target_categories_normalized} para códigos de opção da Embrapa.")
    
    # Primeiro, obter metadados para todas as opções conhecidas para mapear nomes normalizados para códigos
    discovered_options_map = {} # Mapa de nome normalizado para código de opção
    for opt_code_candidate in ALL_KNOWN_OPTIONS:
        _, _, _, main_opt_name_candidate_norm = get_page_metadata(opt_code_candidate, DEFAULT_YEAR_FOR_METADATA_DISCOVERY)
        if main_opt_name_candidate_norm:
            discovered_options_map[main_opt_name_candidate_norm] = opt_code_candidate
            logger.debug(f"Descoberto: '{main_opt_name_candidate_norm}' -> {opt_code_candidate}")
        else:
            logger.warning(f"Não foi possível obter o nome normalizado para o código de opção {opt_code_candidate} usando o ano {DEFAULT_YEAR_FOR_METADATA_DISCOVERY}.")


    for target_cat_norm in target_categories_normalized:
        if target_cat_norm in discovered_options_map:
            opt_code = discovered_options_map[target_cat_norm]
            options_to_scrape_details.append({
                "code": opt_code,
                "display_name_normalized": target_cat_norm 
            })
            logger.info(f"Categoria solicitada '{target_cat_norm}' mapeada para o código de opção da Embrapa '{opt_code}'.")
        else:
            logger.warning(f"Categoria solicitada '{target_cat_norm}' não corresponde a nenhuma aba principal conhecida/descoberta da Embrapa. Será ignorada.")
            logger.debug(f"Opções descobertas disponíveis: {list(discovered_options_map.keys())}")


    if not options_to_scrape_details:
        logger.warning(f"Nenhum código de opção da Embrapa correspondente encontrado para as categorias solicitadas: {target_categories_normalized}.")
        return []

    for opt_detail in options_to_scrape_details:
        opt_code = opt_detail["code"]
        main_opt_display_name_norm = opt_detail["display_name_normalized"] # Este nome já está normalizado

        logger.info(f"\n>>> Processando Opção Filtrada: {opt_code} ({main_opt_display_name_norm}) <<<")
        
        # Obter metadados novamente para a opção correspondente para determinar seu intervalo de anos e subopções específicos.
        min_year_meta, max_year_meta, sub_options_list, _ = get_page_metadata(opt_code, DEFAULT_YEAR_FOR_METADATA_DISCOVERY)

        if min_year_meta is None or max_year_meta is None:
            logger.warning(f"Não foi possível determinar o intervalo de anos para a opção {opt_code} ({main_opt_display_name_norm}). Pulando esta categoria.")
            continue

        # Determinar o intervalo de anos real para raspagem: interseção da solicitação do usuário e disponibilidade da opção.
        actual_scrape_start_year = max(start_year_filter, min_year_meta)
        actual_scrape_end_year = min(end_year_filter, max_year_meta)
        
        if actual_scrape_start_year > actual_scrape_end_year:
            logger.info(f"Pulando {opt_code} ({main_opt_display_name_norm}): intervalo de anos solicitado [{start_year_filter}-{end_year_filter}] "
                        f"não se sobrepõe ao intervalo de dados disponível da opção [{min_year_meta}-{max_year_meta}]. "
                        f"Intervalo efetivo para esta opção seria [{actual_scrape_start_year}-{actual_scrape_end_year}].")
            continue

        logger.info(f"Raspando {opt_code} ({main_opt_display_name_norm}) para os anos: {actual_scrape_start_year} a {actual_scrape_end_year}")
        if sub_options_list:
            logger.info(f"Subopções encontradas para {main_opt_display_name_norm}: {[(s['code'], s['name']) for s in sub_options_list]}")
        else:
            logger.info(f"Nenhuma subopção encontrada para {opt_code} ({main_opt_display_name_norm}).")

        for year_to_scrape in range(actual_scrape_start_year, actual_scrape_end_year + 1):
            if not sub_options_list or opt_code == "opt_01": # opt_01 (Resumo) geralmente não tem sub-opções com tabelas de dados
                logger.info(f"\n--- Raspando: {main_opt_display_name_norm} | Ano: {year_to_scrape} ---")
                time.sleep(0.5) 
                scraped_data_item = get_data_from_embrapa(year_to_scrape, opt_code, None,
                                                          json_aba_name=main_opt_display_name_norm,
                                                          json_subopcao_name=None)
                if scraped_data_item and scraped_data_item.get("dados"):
                    all_scraped_data.append(scraped_data_item)
                elif scraped_data_item:
                    logger.info(f"Nenhuma linha de dados encontrada para {main_opt_display_name_norm} no ano {year_to_scrape}")
            else:
                for sub_opt_detail in sub_options_list:
                    sub_opt_code_val = sub_opt_detail['code']
                    sub_opt_name_norm = sub_opt_detail['name'] # Já está normalizado
                    logger.info(f"\n--- Raspando: {main_opt_display_name_norm} / {sub_opt_name_norm} | Ano: {year_to_scrape} ---")
                    time.sleep(0.5) 
                    scraped_data_item = get_data_from_embrapa(year_to_scrape, opt_code, sub_opt_code_val,
                                                              json_aba_name=main_opt_display_name_norm,
                                                              json_subopcao_name=sub_opt_name_norm)
                    if scraped_data_item and scraped_data_item.get("dados"):
                        all_scraped_data.append(scraped_data_item)
                    elif scraped_data_item:
                        logger.info(f"Nenhuma linha de dados para {main_opt_display_name_norm}/{sub_opt_name_norm} no ano {year_to_scrape}")
    
    total_entries = len(all_scraped_data)
    total_individual_records = sum(len(item.get('dados', [])) for item in all_scraped_data)

    logger.info(f"\n\nProcessamento de Raspagem Filtrada Concluído.")
    logger.info(f"Total de combinações (ano/aba/subopção) com dados: {total_entries}")
    logger.info(f"Total de registros individuais de dados (linhas de tabela): {total_individual_records}")

    if all_scraped_data and output_filepath:
        try:
            output_dir = os.path.dirname(output_filepath)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
            with open(output_filepath, 'w', encoding='utf-8') as f:
                json.dump(all_scraped_data, f, ensure_ascii=False, indent=2)
            logger.info(f"Dados raspados (filtrados) também salvos em: {output_filepath}")
        except Exception as e:
            logger.error(f"Erro ao salvar arquivo JSON de cache (filtrado) em {output_filepath}: {e}")
    elif not all_scraped_data and output_filepath:
        logger.warning("Nenhum dado foi coletado (filtrado) para salvar no arquivo JSON.")
        
    return all_scraped_data


if __name__ == '__main__':
    # Configuração básica de logging para teste local
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(module)s - %(message)s')
    
    # Teste da raspagem completa
    logger.info("--- INICIANDO TESTE DE RASPAGEM COMPLETA ---")
    # Definir um caminho para o arquivo de cache se desejar salvar a saída
    cache_dir = "data_cache_test"
    full_scrape_output_file = os.path.join(cache_dir, "vitibrasil_full_data_test.json")
    # run_full_scrape(output_filepath=full_scrape_output_file)
    logger.info("--- TESTE DE RASPAGEM COMPLETA CONCLUÍDO ---")

    # Teste da raspagem filtrada
    logger.info("\n--- INICIANDO TESTE DE RASPAGEM FILTRADA ---")
    filtered_scrape_output_file = os.path.join(cache_dir, "vitibrasil_filtered_data_test.json")
    
    # Exemplo de categorias e anos para o teste filtrado
    # Lembre-se que as categorias aqui devem ser os nomes normalizados das abas
    # que você espera que get_page_metadata retorne.
    # Por exemplo, se a aba é "Produção", o normalizado é "producao".
    test_categories_norm = ["producao", "comercializacao", "exportacao"] # Usar nomes normalizados
    test_start_year = 2020
    test_end_year = 2022
    
    # run_filtered_scrape(
    #     target_categories_normalized=test_categories_norm,
    #     start_year_filter=test_start_year,
    #     end_year_filter=test_end_year,
    #     output_filepath=filtered_scrape_output_file
    # )
    logger.info("--- TESTE DE RASPAGEM FILTRADA CONCLUÍDO ---")

    # Teste para uma categoria que pode não existir ou nome diferente
    logger.info("\n--- INICIANDO TESTE DE RASPAGEM FILTRADA (CATEGORIA INVÁLIDA) ---")
    # run_filtered_scrape(
    #     target_categories_normalized=["categoria_inexistente", "producao"],
    #     start_year_filter=2021,
    #     end_year_filter=2021,
    #     output_filepath=os.path.join(cache_dir, "vitibrasil_filtered_invalid_cat_test.json")
    # )
    logger.info("--- TESTE DE RASPAGEM FILTRADA (CATEGORIA INVÁLIDA) CONCLUÍDO ---")

    # Teste de normalização
    # print(f"Normalizado 'Produção': {normalize_text('Produção')}")
    # print(f"Normalizado 'Comercialização': {normalize_text('Comercialização')}")
    # print(f"Normalizado 'Processamento - Vinhos de Mesa': {normalize_text('Processamento - Vinhos de Mesa')}")

    # Teste de get_page_metadata para verificar nomes de abas e sub-opções
    # logger.info("\n--- TESTE get_page_metadata ---")
    # for opt_c in ALL_KNOWN_OPTIONS:
    #     m_year, max_y, s_opts, main_n = get_page_metadata(opt_c, 2022)
    #     logger.info(f"Opt: {opt_c} -> Nome Aba Norm: '{main_n}', Anos: [{m_year}-{max_y}], Sub-Opções: {s_opts}")

    from datetime import datetime # Import datetime for the main block
    logger.info(f"Script de raspagem finalizado em {datetime.now()}")
