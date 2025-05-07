from sqlalchemy import Column, Integer, String, Float
from src.app.config.database import Base

class Viticultura(Base):
    __tablename__ = "viticultura"

    id = Column(Integer, primary_key=True, index=True)
    ano = Column(Integer, nullable=False)
    estado = Column(String, nullable=False)
    municipio = Column(String, nullable=False)
    categoria = Column(String, nullable=False)  # ex: produção, exportação etc.
    produto = Column(String, nullable=False)
    quantidade = Column(Float, nullable=False)
    unidade = Column(String, nullable=False) 