from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict
import logging
from src.app.models.viticulture import Viticultura as ViticulturaModel
from src.app.domain.viticulture import ViticulturaCreate
logger = logging.getLogger(__name__)

def get_all_data_by_option(db: Session, opcao: str, ano_minimo: int) -> List[Dict]:
    """
    Busca todos os dados históricos para uma opção específica a partir de um ano mínimo
    """
    try:
        results = db.query(ViticulturaModel).filter(
            ViticulturaModel.aba.ilike(f"%{opcao}%"),
            ViticulturaModel.ano >= ano_minimo
        ).order_by(ViticulturaModel.ano.asc()).all()
        
        data_list = []
        for result in results:
            data_list.append({
                'id': result.id,
                'ano': result.ano,
                'aba': result.aba,
                'subopcao': result.subopcao,
                'dados_list_json': result.dados_list_json,
                'data_raspagem': result.data_raspagem
            })
        
        logger.info(f"Encontrados {len(data_list)} registros para '{opcao}' a partir de {ano_minimo}")
        return data_list
        
    except Exception as e:
        logger.error(f"Erro ao buscar dados por opção: {e}")
        raise

def save_bulk(db: Session, data_list: List[ViticulturaCreate]):
    """
    Saves a list of ViticulturaCreate objects to the database.
    This version does NOT delete old data, allowing for a history of scrapes.
    """
    db_data_list = []
    for data_item in data_list:
        db_item = ViticulturaModel(
            ano=data_item.ano,
            aba=data_item.aba,
            subopcao=data_item.subopcao,
            dados_list_json=data_item.dados, # Mapear para o nome correto da coluna
            data_raspagem=data_item.data_raspagem # Salvar o timestamp
        )
        db_data_list.append(db_item)
    
    try:
        db.add_all(db_data_list)
        db.commit()
        logger.info(f"Dados em lote salvos com sucesso: {len(db_data_list)} entradas.")
        for db_item in db_data_list: # Para popular IDs se necessário, embora não usado diretamente aqui
            db.refresh(db_item)
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao salvar dados em lote: {e}")
        raise



def get_latest_scrape_group(db: Session) -> List[ViticulturaModel]:
    """
    Retrieves all viticulture data entries from the most recent scrape.
    Returns a list of Viticultura SQLAlchemy model instances.
    """
    try:
        # Encontrar o timestamp da raspagem mais recente
        latest_timestamp = db.query(func.max(ViticulturaModel.data_raspagem)).scalar()

        if not latest_timestamp:
            logger.info("Nenhum timestamp de raspagem encontrado no banco de dados.")
            return []

        logger.info(f"Timestamp da raspagem mais recente encontrado: {latest_timestamp}")
        return db.query(ViticulturaModel).filter(ViticulturaModel.data_raspagem == latest_timestamp).all()
    except Exception as e:
        logger.error(f"Erro ao buscar o grupo de raspagem mais recente: {e}")
        raise 

def get_specific_data_from_db(db: Session, ano_min: int, ano_max: int, opcao: str):
    try:
        query = db.query(ViticulturaModel).filter(
            ViticulturaModel.ano >= ano_min,
            ViticulturaModel.ano <= ano_max,
            ViticulturaModel.aba.ilike(f"%{opcao}%")
        ).order_by(ViticulturaModel.data_raspagem.desc())
        return query.all()
    except Exception as e:
        logger.error(f"Erro ao buscar dados específicos do banco: {e}")
        return []    