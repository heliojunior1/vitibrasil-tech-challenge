from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any # Ensure Dict and Any are imported

# This model can represent the structure of individual items within the 'dados' list
# It's good for documentation and validation if the structure is consistent.
# If highly variable, List[Dict[str, Any]] is more flexible for 'dados_list_json'.
class DadoItem(BaseModel):
    # Example fields, adjust based on what your scraper actually produces within the 'dados' list
    # produto: Optional[str] = None
    # cultivar: Optional[str] = None
    # quantidade: Optional[float] = None
    # valor: Optional[float] = None
    # categoria_tabela: Optional[str] = None 
    # ... any other fields ...

    class Config:
        extra = 'allow' # Allows fields not explicitly defined in DadoItem, useful for varying table structures

class ViticulturaBase(BaseModel):
    ano: int = Field(..., description="Ano a que os dados se referem")
    aba: str = Field(..., description="Nome normalizado da aba principal (e.g., 'producao', 'comercializacao')")
    subopcao: Optional[str] = Field(None, description="Nome normalizado da subopção, se aplicável (e.g., 'vinho_de_mesa')")
    
    # This will hold the list of dictionaries directly from the scraper's 'dados' field.
    # When reading from DB, it will be populated from the 'dados_list_json' column.
    # When creating, the service will pass the scraper's 'dados' list to this field.
    dados: List[Dict[str, Any]] = Field(..., description="Lista de registros de dados detalhados da tabela")
    # If you prefer to use the DadoItem model for stronger typing of the list items:
    # dados: List[DadoItem] = Field(..., description="Lista de registros de dados detalhados da tabela")


class ViticulturaCreate(ViticulturaBase):
    # No additional fields needed for creation if ViticulturaBase covers all inputs
    # This model will be used to validate the data structure coming from the scraper
    # before it's passed to the repository for saving.
    pass


class ViticulturaResponse(ViticulturaBase):
    id: int = Field(..., description="ID único do registro no banco de dados")

    class Config:
        from_attributes = True # Changed from orm_mode = True for Pydantic v2
        # This allows the model to be created from ORM objects directly.

# This model can be used for the overall API response if you're returning a list of these items.
class ViticulturaListResponse(BaseModel):
    fonte: str = Field(..., description="Fonte dos dados (e.g., 'Embrapa (Raspagem Ao Vivo)', 'Cache (BD)')")
    dados: List[ViticulturaResponse] = Field(..., description="Lista de entradas de dados de viticultura")
    message: Optional[str] = Field(None, description="Mensagem adicional")
