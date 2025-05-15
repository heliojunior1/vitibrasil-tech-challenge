from pydantic import BaseModel, Field, validator
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

class DadosEspecificosRequest(BaseModel):
    ano_min: int = Field(..., ge=1970, le=2023, description="Ano mínimo (1970-2023)")
    ano_max: int = Field(..., ge=1970, le=2023, description="Ano máximo (1970-2023)")
    opcao: str = Field(..., description="Opção: 'producao', 'processamento', 'comercializacao', 'importacao', 'exportacao'")

    @validator('opcao')
    def validate_opcao(cls, v):
        opcoes_validas = ['producao', 'processamento', 'comercializacao', 'importacao', 'exportacao']
        if v not in opcoes_validas:
            raise ValueError(f"Opção deve ser uma das seguintes: {opcoes_validas}")
        return v

    @validator('ano_max')
    def validate_anos(cls, v, values):
        if 'ano_min' in values and v < values['ano_min']:
            raise ValueError("ano_max deve ser maior ou igual a ano_min")
        return v