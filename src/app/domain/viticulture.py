from pydantic import BaseModel
from typing import Optional

class ViticulturaDTO(BaseModel):
    ano: int
    estado: str
    municipio: str
    categoria: str
    produto: str
    quantidade: float
    unidade: str

    class Config:
        orm_mode = True