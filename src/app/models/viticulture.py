from sqlalchemy import Column, Integer, String, JSON, DateTime
from sqlalchemy.ext.declarative import declarative_base
from src.app.config.database import Base
from datetime import datetime


class Viticultura(Base):
    __tablename__ = "viticultura_data" # Using a more descriptive table name

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    ano = Column(Integer, index=True, nullable=False)
    aba = Column(String, index=True, nullable=False) 
    subopcao = Column(String, index=True, nullable=True) 
    
    dados_list_json = Column(JSON, nullable=False) 
    data_raspagem = Column(DateTime, default=datetime.utcnow, nullable=False, index=True) 


    def __repr__(self):
        return f"<Viticultura(id={self.id}, ano={self.ano}, aba='{self.aba}', subopcao='{self.subopcao}', records_count={len(self.dados_list_json) if self.dados_list_json else 0})>"