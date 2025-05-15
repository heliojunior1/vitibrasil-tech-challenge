import os
import json
import time
import logging
from .viticulture_scraper_base import get_page_metadata, get_data_from_embrapa

logger = logging.getLogger(__name__)

def run_full_scrape(output_filepath: str = None) -> list:
    MAIN_OPTIONS_TO_SCRAPE = ["opt_02", "opt_03", "opt_04", "opt_05", "opt_06"]
    all_scraped_data = []
    DEFAULT_YEAR_FOR_METADATA_DISCOVERY = 2023
    FALLBACK_MIN_YEAR = 2023
    FALLBACK_MAX_YEAR = 2023

    for opt_code in MAIN_OPTIONS_TO_SCRAPE:
        logger.info(f"\n>>> Processing Main Option Code: {opt_code} <<<")
        min_year_meta, max_year_meta, sub_options_list, main_opt_display_name = get_page_metadata(opt_code, DEFAULT_YEAR_FOR_METADATA_DISCOVERY)
        logger.info(f"Descriptive name for {opt_code}: {main_opt_display_name}")
        current_min_year = 2023
        # current_min_year = min_year_meta if min_year_meta is not None else FALLBACK_MIN_YEAR 
        current_max_year = max_year_meta if max_year_meta is not None else FALLBACK_MAX_YEAR
        
        logger.info(f"Scraping {opt_code} ({main_opt_display_name}) for years: {current_min_year} to {current_max_year}")
        if sub_options_list:
            logger.info(f"Found suboptions: {[(s['code'], s['name']) for s in sub_options_list]}")
        else:
            logger.info(f"No suboptions found for {opt_code} ({main_opt_display_name}).")

        for year_to_scrape in range(current_min_year, current_max_year + 1):
            if not sub_options_list:
                logger.info(f"\n--- Scraping: {opt_code} ({main_opt_display_name}) | Ano: {year_to_scrape} ---")
                time.sleep(0.5)
                scraped_data_item = get_data_from_embrapa(year_to_scrape, opt_code, None,
                                                          json_aba_name=main_opt_display_name,
                                                          json_subopcao_name=None)
                if scraped_data_item and scraped_data_item.get("dados"):
                    all_scraped_data.append(scraped_data_item)
                elif scraped_data_item:
                    logger.info(f"No data rows found for {opt_code} ({main_opt_display_name}) for year {year_to_scrape}")
            else:
                for sub_opt_detail in sub_options_list:
                    logger.info(f"\n--- Scraping: {opt_code}/{sub_opt_detail['code']} ({main_opt_display_name}/{sub_opt_detail['name']}) | Ano: {year_to_scrape} ---")
                    time.sleep(0.5)
                    scraped_data_item = get_data_from_embrapa(year_to_scrape, opt_code, sub_opt_detail['code'],
                                                              json_aba_name=main_opt_display_name,
                                                              json_subopcao_name=sub_opt_detail['name'])
                    if scraped_data_item and scraped_data_item.get("dados"):
                        all_scraped_data.append(scraped_data_item)
                    elif scraped_data_item:
                        logger.info(f"No data rows for {opt_code}/{sub_opt_detail['code']} ({main_opt_display_name}/{sub_opt_detail['name']}) for year {year_to_scrape}")

    total_entries = len(all_scraped_data)
    total_individual_records = sum(len(item.get('dados', [])) for item in all_scraped_data)

    logger.info(f"\n\nProcessamento Concluído.")
    logger.info(f"Total de combinações (ano/aba/subopção) com dados: {total_entries}")
    logger.info(f"Total de registros individuais de dados (linhas de tabela): {total_individual_records}")

    if all_scraped_data and output_filepath:
        try:
            output_dir = os.path.dirname(output_filepath)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)

            with open(output_filepath, 'w', encoding='utf-8') as f:
                json.dump(all_scraped_data, f, ensure_ascii=False, indent=2)
            logger.info(f"Dados raspados também salvos em: {output_filepath}")
        except Exception as e:
            logger.error(f"Erro ao salvar arquivo JSON de cache em {output_filepath}: {e}")
    elif not all_scraped_data and output_filepath:
        logger.warning("Nenhum dado foi coletado para salvar no arquivo JSON.")

    return all_scraped_data


if __name__ == '__main__':
    # Este bloco é para execução direta do script, útil para testes.
    actual_min_year_scraped = 2023 
    actual_max_year_scraped = 2023
    file_out_name = f"dados_embrapa_vitibrasil_{actual_min_year_scraped}_a_{actual_max_year_scraped}_descritivo_TEST.json"
    logger.info(f"Executando raspagem de teste, saída para: {file_out_name}")
    scraped_results = run_full_scrape(output_filepath=file_out_name)
    
    if not scraped_results:
        logger.info("Nenhum dado foi coletado durante a execução de teste.")