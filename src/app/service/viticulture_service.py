from app.scraper.scraper import get_data_from_embrapa
from app.repository.viticulture_repo import get_all, save
from app.config.database import SessionLocal

def obter_dados():
    session = SessionLocal()
    try:
        dados = get_data_from_embrapa()
        save(session, dados)
        return {"fonte": "Embrapa", "dados": dados}
    except:
        dados_cache = get_all(session)
        return {"fonte": "Cache (BD)", "dados": dados_cache}