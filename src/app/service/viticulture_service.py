from sqlalchemy.orm import Session
from typing import List, Dict, Any
from fastapi import BackgroundTasks 
from src.app.scraper.viticulture_full_scraper import run_full_scrape
from src.app.scraper.viticulture_partial_scraper import run_scrape_by_params
from src.app.repository.viticulture_repo import save_bulk, get_latest_scrape_group # Alterado aqui
from src.app.domain.viticulture import ViticulturaCreate, ViticulturaResponse, ViticulturaListResponse
from src.app.config.database import SessionLocal 
import logging
from datetime import datetime # Adicionar datetime
from src.app.domain.viticulture import DadosEspecificosRequest




logger = logging.getLogger(__name__)

def _save_data_in_background(data_to_save: List[ViticulturaCreate]):
    db_bg = SessionLocal()
    try:
        logger.info(f"Background task: Iniciando salvamento de {len(data_to_save)} registros.")
        save_bulk(db_bg, data_to_save) 
        logger.info("Background task: Dados salvos com sucesso no banco de dados.")
    except Exception as e_save_bg:
        logger.error(f"Background task: Erro ao salvar dados no banco de dados: {e_save_bg}")
    finally:
        db_bg.close()
        logger.info("Background task: Sessão do banco de dados fechada.")

def obter_dados_viticultura_e_salvar(db: Session, background_tasks: BackgroundTasks):
    fonte_mensagem = "Falha ao obter dados"
    data_for_response: List[ViticulturaResponse] = []
    mensagem_adicional = None
    current_timestamp = datetime.utcnow() # Timestamp para esta tentativa de raspagem

    try:
        logger.info("Tentando raspar dados ao vivo da Embrapa...")
        scraped_data_list = run_full_scrape(output_filepath=None)

        if scraped_data_list and any(item.get('dados') for item in scraped_data_list):
            logger.info(f"Raspagem ao vivo bem-sucedida. {len(scraped_data_list)} seções de dados obtidas.")
            
            viticultura_create_list: List[ViticulturaCreate] = []
            for item_dict in scraped_data_list:
                try:
                    vc = ViticulturaCreate(
                        ano=item_dict['ano'],
                        aba=item_dict['aba'],
                        subopcao=item_dict.get('subopcao'),
                        dados=item_dict['dados'],
                        data_raspagem=current_timestamp # Adicionar timestamp
                    )
                    viticultura_create_list.append(vc)
                except KeyError as ke:
                    logger.error(f"Alerta: Item raspado ignorado devido à chave ausente: {ke}. Item: {item_dict}")
                    continue
                except Exception as p_exc: 
                    logger.error(f"Alerta: Item raspado ignorado devido a erro de validação/criação: {p_exc}. Item: {item_dict}")
                    continue

            if not viticultura_create_list:
                logger.info("Nenhum dado válido para salvar após a transformação da raspagem.")
                mensagem_adicional = "Raspagem ao vivo não produziu dados válidos para o banco de dados."
            else:
                logger.info(f"Transformação concluída. {len(viticultura_create_list)} entradas prontas para retornar e salvar.")
                
                for vc_item in viticultura_create_list:
                    data_for_response.append(ViticulturaResponse(
                        id=None, # id será None pois ainda não foi salvo
                        ano=vc_item.ano,
                        aba=vc_item.aba,
                        subopcao=vc_item.subopcao,
                        dados=vc_item.dados,
                        data_raspagem=vc_item.data_raspagem
                    ))

                fonte_mensagem = "Embrapa (Raspagem Ao Vivo - Salvamento em Andamento)"
                background_tasks.add_task(_save_data_in_background, viticultura_create_list)
                
                return ViticulturaListResponse(
                    fonte=fonte_mensagem, 
                    dados=data_for_response, 
                    message=f"Dados de raspagem ao vivo ({current_timestamp.isoformat()}) retornados. Salvamento no banco de dados iniciado em background."
                )
        else: 
            logger.info("Raspagem ao vivo não retornou dados ou os dados estavam vazios. Tentando cache do BD.")
            mensagem_adicional = "Raspagem ao vivo não retornou dados. Usando cache do BD se disponível."

    except Exception as e_scrape: 
        logger.error(f"Falha crítica na raspagem ao vivo: {e_scrape}. Tentando cache do BD.")
        mensagem_adicional = f"Falha na raspagem ao vivo: {e_scrape}. Usando cache do BD se disponível."

    logger.info("Tentando carregar dados do cache do banco de dados (raspagem mais recente)...")
    try:
        db_data_models = get_latest_scrape_group(db) # Alterado aqui
        if db_data_models:
            # O Pydantic model ViticulturaResponse espera 'dados', mas o DB model tem 'dados_list_json'
            # e também precisamos do 'data_raspagem' do modelo do banco.
            for db_item in db_data_models:
                data_for_response.append(ViticulturaResponse(
                    id=db_item.id,
                    ano=db_item.ano,
                    aba=db_item.aba,
                    subopcao=db_item.subopcao,
                    dados=db_item.dados_list_json, # Mapear do nome da coluna do DB
                    data_raspagem=db_item.data_raspagem
                ))
            
            latest_db_timestamp_str = data_for_response[0].data_raspagem.isoformat() if data_for_response else "N/A"
            logger.info(f"Dados carregados com sucesso do cache do banco de dados (raspagem de {latest_db_timestamp_str}): {len(data_for_response)} entradas.")
            fonte_mensagem = f"Cache (Banco de Dados - Raspagem de {latest_db_timestamp_str})"
            if mensagem_adicional: 
                fonte_mensagem = f"{fonte_mensagem} (após: {mensagem_adicional.split('.')[0]})"
            else: 
                 mensagem_adicional = f"Raspagem ao vivo não produziu dados válidos, servindo do cache do BD (raspagem de {latest_db_timestamp_str})."
        else: 
            logger.warning("Nenhum dado encontrado no cache do banco de dados.")
            fonte_mensagem = "Falha - Cache do BD Vazio"
            if not mensagem_adicional:
                mensagem_adicional = "Nenhum dado encontrado na Embrapa (raspagem) nem no cache do BD."
            else:
                mensagem_adicional += " Cache do BD também está vazio."
                
    except Exception as e_db_cache:
        logger.error(f"Erro ao carregar dados do cache do banco de dados: {e_db_cache}")
        fonte_mensagem = "Falha - Erro ao Ler Cache do BD"
        if not mensagem_adicional:
            mensagem_adicional = f"Erro ao ler cache do BD: {e_db_cache}"
        else:
            mensagem_adicional += f" Erro ao ler cache do BD: {e_db_cache}."

    return ViticulturaListResponse(
        fonte=fonte_mensagem, 
        dados=data_for_response, 
        message=mensagem_adicional
    )


def buscar_dados_especificos(db: Session, background_tasks: BackgroundTasks, ano_min: int, ano_max: int, opcao: str):
    from src.app.scraper.viticulture_partial_scraper import run_scrape_by_params
    from src.app.repository.viticulture_repo import get_specific_data_from_db

    fonte_mensagem = "Falha ao obter dados"
    data_for_response: List[ViticulturaResponse] = []
    mensagem_adicional = None
    current_timestamp = datetime.utcnow()

    try:
        scraped_data_list = run_scrape_by_params(ano_min, ano_max, opcao)
        if scraped_data_list and any(item.get('dados') for item in scraped_data_list):
            viticultura_create_list: List[ViticulturaCreate] = []
            for item_dict in scraped_data_list:
                try:
                    vc = ViticulturaCreate(
                        ano=item_dict['ano'],
                        aba=item_dict['aba'],
                        subopcao=item_dict.get('subopcao'),
                        dados=item_dict['dados'],
                        data_raspagem=current_timestamp
                    )
                    viticultura_create_list.append(vc)
                except Exception as e:
                    logger.error(f"Erro ao processar item raspado: {e}")
                    continue
            for vc_item in viticultura_create_list:
                data_for_response.append(ViticulturaResponse(
                    id=None,
                    ano=vc_item.ano,
                    aba=vc_item.aba,
                    subopcao=vc_item.subopcao,
                    dados=vc_item.dados,
                    data_raspagem=vc_item.data_raspagem
                ))
            fonte_mensagem = "Embrapa (Raspagem Específica - Salvamento em Andamento)"
            background_tasks.add_task(_save_data_in_background, viticultura_create_list)
            return ViticulturaListResponse(
                fonte=fonte_mensagem,
                dados=data_for_response,
                message=f"Dados de raspagem ({ano_min}-{ano_max}, {opcao}) retornados. Salvamento no banco de dados iniciado em background."
            )
        else:
            mensagem_adicional = "Raspagem ao vivo não retornou dados. Usando cache do BD se disponível."
    except Exception as e:
        logger.error(f"Erro na raspagem ao vivo: {e}. Tentando cache do BD.")
        mensagem_adicional = "Erro na raspagem ao vivo. Usando cache do BD se disponível."

    db_data = get_specific_data_from_db(db, ano_min, ano_max, opcao)
    if db_data:
        for db_item in db_data:
            data_for_response.append(ViticulturaResponse(
                id=db_item.id,
                ano=db_item.ano,
                aba=db_item.aba,
                subopcao=db_item.subopcao,
                dados=db_item.dados_list_json,
                data_raspagem=db_item.data_raspagem
            ))
        fonte_mensagem = f"Cache (Banco de Dados - {opcao}, {ano_min}-{ano_max})"
        return ViticulturaListResponse(
            fonte=fonte_mensagem,
            dados=data_for_response,
            message=mensagem_adicional or "Dados servidos do cache do banco de dados."
        )
    else:
        fonte_mensagem = "Falha - Cache do BD Vazio"
        return ViticulturaListResponse(
            fonte=fonte_mensagem,
            dados=[],
            message=mensagem_adicional or "Nenhum dado encontrado na Embrapa nem no cache do BD."
        )