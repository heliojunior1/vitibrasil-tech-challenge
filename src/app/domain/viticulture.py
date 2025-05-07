from sqlalchemy import Column, Integer, String
from src.app.config.database import Base

class Viticultura(Base):
    __tablename__ = "viticultura"

    id = Column(Integer, primary_key=True, index=True)
    tipo = Column(String)
    valor = Column(String)