from sqlalchemy.orm import Session
from typing import List, Dict, Any

# Scraper function
from src.app.scraper.viticulture_scraper import run_full_scrape, CACHED_DATA_FILENAME # CACHED_DATA_FILENAME might not be used if DB is primary cache
# Repository functions
from src.app.repository.viticulture_repo import save_bulk, get_all as get_all_from_db
# Pydantic domain models
from src.app.domain.viticulture import ViticulturaCreate, ViticulturaResponse, ViticulturaListResponse
# Database session
from src.app.config.database import SessionLocal # To create a session if not passed in

# For determining cache file path if you still want a JSON backup, though primary is DB now
import os
SERVICE_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SERVICE_FILE_DIR, "..", "..", ".."))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
JSON_CACHE_FILE_FULL_PATH = os.path.join(DATA_DIR, CACHED_DATA_FILENAME) # e.g., data/vitibrasil_data_cache.json

def obter_dados_viticultura_e_salvar(db: Session): # Renamed for clarity
    """
    Attempts to scrape live viticulture data, saves it to the database,
    and returns it. If scraping fails, attempts to load data from the database.
    """
    fonte_mensagem = "Falha ao obter dados"
    dados_retornados = []
    mensagem_adicional = None

    try:
        print("Tentando raspar dados ao vivo da Embrapa...")
        # run_full_scrape expects an output_filepath for its own JSON dump,
        # which can serve as a raw backup or for debugging.
        # We'll use the JSON_CACHE_FILE_FULL_PATH for this.
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR, exist_ok=True)
            print(f"Diretório de cache JSON criado: {DATA_DIR}")

        scraped_data_list = run_full_scrape(output_filepath=JSON_CACHE_FILE_FULL_PATH)

        if scraped_data_list and any(item.get('dados') for item in scraped_data_list):
            print(f"Raspagem ao vivo bem-sucedida. {len(scraped_data_list)} seções de dados obtidas.")
            
            # Transform scraped data into List[ViticulturaCreate]
            viticultura_create_list = []
            for item_dict in scraped_data_list:
                # Ensure all required fields for ViticulturaCreate are present in item_dict
                # 'ano', 'aba', 'dados' are expected from the scraper's output structure
                try:
                    vc = ViticulturaCreate(
                        ano=item_dict['ano'],
                        aba=item_dict['aba'], # This is 'main_opt_display_name' from scraper
                        subopcao=item_dict.get('subopcao'), # This is 'sub_opt_detail_name'
                        dados=item_dict['dados'] # This is the list of data rows
                    )
                    viticultura_create_list.append(vc)
                except KeyError as ke:
                    print(f"Alerta: Item raspado ignorado devido à chave ausente: {ke}. Item: {item_dict}")
                    continue # Skip this item
                except Exception as p_exc: # Catch Pydantic validation errors or other issues
                    print(f"Alerta: Item raspado ignorado devido a erro de validação/criação: {p_exc}. Item: {item_dict}")
                    continue


            if not viticultura_create_list:
                print("Nenhum dado válido para salvar após a transformação da raspagem.")
                mensagem_adicional = "Raspagem ao vivo não produziu dados válidos para o banco de dados."
                # Fall through to DB cache attempt
            else:
                print(f"Transformação concluída. {len(viticultura_create_list)} entradas prontas para o BD.")
                try:
                    save_bulk(db, viticultura_create_list)
                    print("Dados raspados salvos com sucesso no banco de dados.")
                    fonte_mensagem = "Embrapa (Raspagem Ao Vivo e Salvo no BD)"
                    
                    # Retrieve again from DB to ensure we return data with IDs and consistent with DB state
                    db_data_models = get_all_from_db(db)
                    # Convert SQLAlchemy models to Pydantic ViticulturaResponse models
                    dados_retornados = [ViticulturaResponse.model_validate(db_item) for db_item in db_data_models]
                    # Pydantic v1: dados_retornados = [ViticulturaResponse.from_orm(db_item) for db_item in db_data_models]

                    return ViticulturaListResponse(fonte=fonte_mensagem, dados=dados_retornados, message=mensagem_adicional)

                except Exception as e_save:
                    db.rollback() # Ensure rollback if save_bulk raised an error that wasn't caught inside it
                    print(f"Erro ao salvar dados raspados no banco de dados: {e_save}")
                    mensagem_adicional = f"Falha ao salvar dados raspados no BD: {e_save}. Tentando cache do BD."
                    # Fall through to DB cache attempt
        else:
            print("Raspagem ao vivo não retornou dados ou os dados estavam vazios. Tentando cache do BD.")
            mensagem_adicional = "Raspagem ao vivo não retornou dados. Usando cache do BD se disponível."

    except Exception as e_scrape:
        print(f"Falha crítica na raspagem ao vivo: {e_scrape}. Tentando cache do BD.")
        mensagem_adicional = f"Falha na raspagem ao vivo: {e_scrape}. Usando cache do BD se disponível."

    # Fallback: If scraping failed or produced no data to save, try loading from DB
    print("Tentando carregar dados do cache do banco de dados...")
    try:
        db_data_models = get_all_from_db(db)
        if db_data_models:
            # Convert SQLAlchemy models to Pydantic ViticulturaResponse models
            dados_retornados = [ViticulturaResponse.model_validate(db_item) for db_item in db_data_models]
            # Pydantic v1: dados_retornados = [ViticulturaResponse.from_orm(db_item) for db_item in db_data_models]
            
            print(f"Dados carregados com sucesso do cache do banco de dados: {len(dados_retornados)} entradas.")
            fonte_mensagem = "Cache (Banco de Dados)"
            if mensagem_adicional: # Append to existing message if scrape failed
                fonte_mensagem = f"{fonte_mensagem} (após falha na raspagem: {mensagem_adicional.split('.')[0]})"
            else: # If scraping was skipped due to no data
                 mensagem_adicional = "Raspagem ao vivo não produziu dados, servindo do cache do BD."

        else:
            print("Nenhum dado encontrado no cache do banco de dados.")
            fonte_mensagem = "Falha - Cache do BD Vazio"
            if not mensagem_adicional:
                mensagem_adicional = "Nenhum dado encontrado na Embrapa (raspagem) nem no cache do BD."
            else: # Append to existing message
                mensagem_adicional += " Cache do BD também está vazio."
                
    except Exception as e_db_cache:
        db.rollback() # Just in case, though get_all is read-only
        print(f"Erro ao carregar dados do cache do banco de dados: {e_db_cache}")
        fonte_mensagem = "Falha - Erro ao Ler Cache do BD"
        if not mensagem_adicional:
            mensagem_adicional = f"Erro ao ler cache do BD: {e_db_cache}"
        else:
            mensagem_adicional += f" Erro ao ler cache do BD: {e_db_cache}."

    return ViticulturaListResponse(fonte=fonte_mensagem, dados=dados_retornados, message=mensagem_adicional)

# Helper to get a DB session, useful if the route doesn't manage it.
# However, FastAPI's dependency injection for sessions is preferred for routes.
# def get_db_session():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()