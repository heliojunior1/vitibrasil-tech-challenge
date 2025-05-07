from sqlalchemy.orm import Session
from app.domain.models import Viticultura

def get_all(session: Session):
    return session.query(Viticultura).all()

def save(session: Session, dados: list[dict]):
    for item in dados:
        session.add(Viticultura(**item))
    session.commit()