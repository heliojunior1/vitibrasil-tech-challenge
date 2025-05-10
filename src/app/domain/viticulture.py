from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any # Ensure Dict and Any are imported
from datetime import datetime # Adicionar datetime

class DadoItem(BaseModel):

    class Config:
        extra = 'allow' # Allows fields not explicitly defined in DadoItem, useful for varying table structures

class ViticulturaBase(BaseModel):
    ano: int
    aba: str
    subopcao: Optional[str] = None
    dados: List[Dict[str, Any]]
    data_raspagem: datetime # Novo campo

    class Config:
        from_attributes = True
        extra = 'allow' 

class ViticulturaCreate(ViticulturaBase):
    pass


class ViticulturaResponse(ViticulturaBase):
    id: Optional[int] = Field(None, description="ID único do registro no banco de dados, None se dados são de raspagem ao vivo ainda não persistida") # Modified

    class Config:
        from_attributes = True 


# This model can be used for the overall API response if you're returning a list of these items.
class ViticulturaListResponse(BaseModel):
    fonte: str = Field(..., description="Fonte dos dados (e.g., 'Embrapa (Raspagem Ao Vivo)', 'Cache (BD)')")
    dados: List[ViticulturaResponse] = Field(..., description="Lista de entradas de dados de viticultura")
    message: Optional[str] = Field(None, description="Mensagem adicional")
