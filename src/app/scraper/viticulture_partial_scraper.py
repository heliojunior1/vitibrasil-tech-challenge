import logging
from .viticulture_scraper_base import get_page_metadata, get_data_from_embrapa

logger = logging.getLogger(__name__)

def run_scrape_by_params(ano_min: int, ano_max: int, opcao_nome: str) -> list:
    OPCOES = {
        "producao": "opt_02",
        "processamento": "opt_03",
        "comercializacao": "opt_04",
        "importacao": "opt_05",
        "exportacao": "opt_06"
    }
    if opcao_nome not in OPCOES:
        logger.error(f"Opção '{opcao_nome}' inválida. Opções disponíveis: {list(OPCOES.keys())}")
        return []
    if ano_min < 1970 or ano_min > 2023 or ano_max < 1970 or ano_max > 2023:
        logger.error("Anos devem estar entre 1970 e 2023")
        return []
    if ano_min > ano_max:
        logger.error("Ano mínimo deve ser menor ou igual ao ano máximo")
        return []

    opt_code = OPCOES[opcao_nome]
    all_scraped_data = []
    min_year_meta, max_year_meta, sub_options_list, main_opt_display_name = get_page_metadata(opt_code, ano_max)
    for year_to_scrape in range(ano_min, ano_max + 1):
        if not sub_options_list:
            scraped_data_item = get_data_from_embrapa(year_to_scrape, opt_code, None, json_aba_name=main_opt_display_name)
            if scraped_data_item and scraped_data_item.get("dados"):
                all_scraped_data.append(scraped_data_item)
        else:
            for sub_opt_detail in sub_options_list:
                scraped_data_item = get_data_from_embrapa(
                    year_to_scrape, opt_code, sub_opt_detail['code'],
                    json_aba_name=main_opt_display_name,
                    json_subopcao_name=sub_opt_detail['name']
                )
                if scraped_data_item and scraped_data_item.get("dados"):
                    all_scraped_data.append(scraped_data_item)
    return all_scraped_data


if __name__ == '__main__':
    # Este bloco é para execução direta do script, útil para testes.
    ano_min = 2022
    ano_max = 2023
    opcao = "producao"
    
    logger.info(f"Executando raspagem parcial: {opcao} de {ano_min} a {ano_max}")
    scraped_results = run_scrape_by_params(ano_min, ano_max, opcao)
    
    if not scraped_results:
        logger.info("Nenhum dado foi coletado durante a execução de teste.")
    else:
        logger.info(f"Coletados {len(scraped_results)} conjuntos de dados.")