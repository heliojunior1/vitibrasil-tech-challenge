from sqlalchemy import Column, Integer, String, JSON # Add JSON type
from src.app.config.database import Base

class Viticultura(Base):
    __tablename__ = "viticultura_data" # Using a more descriptive table name

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    ano = Column(Integer, index=True, nullable=False)
    aba = Column(String, index=True, nullable=False) # Represents the main option like 'producao', 'comercializacao'
    subopcao = Column(String, index=True, nullable=True) # Represents the sub-option like 'vinho_de_mesa', 'espumantes'
    
    # This field will store the list of data rows (the 'dados' part from the scraper) as a JSON array of objects.
    dados_list_json = Column(JSON, nullable=False) 

    # If you want to add a timestamp for when the data was scraped/cached:
    # from sqlalchemy.sql import func
    # scraped_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Viticultura(id={self.id}, ano={self.ano}, aba='{self.aba}', subopcao='{self.subopcao}', records_count={len(self.dados_list_json) if self.dados_list_json else 0})>"