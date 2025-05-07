from src.app.scraper.viticulture_scraper import get_data_from_embrapa
from src.app.config.database import SessionLocal
from sqlalchemy.orm import Session
from src.app.models.viticulture import Viticultura



def get_all(session: Session):
    return session.query(Viticultura).all()

def save(session: Session, dados: list[dict]):
    for item in dados:
        try:
            session.add(Viticultura(**item))
        except Exception as e:
            print("Erro ao salvar item:", item)
            print("Motivo:", e)
    session.commit()