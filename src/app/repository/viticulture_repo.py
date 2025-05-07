from src.app.scraper.viticulture_scraper import get_data_from_embrapa
from src.app.config.database import SessionLocal
from sqlalchemy.orm import Session


def get_all(session: Session):
    return session.query(Viticultura).all()

def save(session: Session, dados: list[dict]):
    for item in dados:
        session.add(Viticultura(**item))
    session.commit()