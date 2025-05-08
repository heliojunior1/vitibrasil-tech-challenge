from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum

class ViticultureCategory(str, Enum):
    producao = "producao"
    Processamento = "processamento"
    comercializacao = "comercializacao"
    exportacao = "exportacao"
    importacao = "importacao"

class ViticulturaDTO(BaseModel):
    category: ViticultureCategory
    subcategory: Optional[str] = None
    item: str
    year: int
    value: float
    unit: str
    currency: Optional[str] = None
    source_url: Optional[str] = None
    scraped_at: Optional[datetime] = None

    class Config:
        orm_mode = True
