from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum

class ViticultureCategory(str, Enum):
    producao = "opt_02"
    processamento = "opt_03"
    comercializacao = "opt_04"
    exportacao = "opt_05"
    importacao = "opt_06"

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
        from_attributes = True
