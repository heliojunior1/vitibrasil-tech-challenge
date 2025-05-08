from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
from src.app.config.database import get_db
from src.app.domain.viticulture import ViticultureCategory, ViticulturaDTO
from src.app.service.viticulture_service import consultar_dados_com_parametros, consultar_tudo

router = APIRouter(prefix="/viticulture", tags=["Viticulture"])

class ConsultaParametrizadaRequest(BaseModel):
    categoria: ViticultureCategory
    tipo: str
    ano: int
    opcao: str
    subopcao: str

@router.post("/consultar", response_model=List[ViticulturaDTO])
def consultar(request: ConsultaParametrizadaRequest, db: Session = Depends(get_db)):
    return consultar_dados_com_parametros(
        categoria=request.categoria,
        tipo=request.tipo,
        ano=request.ano,
        opcao=request.opcao,
        subopcao=request.subopcao,
        db=db
    )

@router.post("/consultar-tudo")
def consultar_completo(db: Session = Depends(get_db)):
    return consultar_tudo(db)
