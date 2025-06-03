from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class PredictionRequest(BaseModel):
    opcao: str = Field(..., description="Tipo de opção (producao, exportacao, etc.)")
    ano_inicial: int = Field(..., description="Ano mínimo de dados para usar na análise", ge=1970)
    
class PredictionResponse(BaseModel):
    opcao: str
    ano_anterior: int
    quantidade_ano_anterior: float
    ano_previsto: int
    quantidade_prevista: float
    unidade: str
    confianca: float = Field(..., description="Nível de confiança da previsão (0-1)")
    modelo_usado: str
    dados_historicos_anos: int
    data_previsao: datetime
    detalhes: Optional[Dict[str, Any]] = None