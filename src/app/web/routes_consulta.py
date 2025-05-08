from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from src.app.config.database import get_db
from src.app.scraper.viticulture_scraper import buscar_csv_por_categoria
from src.app.domain.viticulture import ViticulturaDTO, ViticultureCategory

router = APIRouter(prefix="/viticulture", tags=["Viticulture"])

class ConsultaRequest(BaseModel):
    categoria: ViticultureCategory
    tipo: str
    ano: int
    opcao: str
    subopcao: str

@router.post("/consultar-site", response_model=List[ViticulturaDTO])
def consultar_site(request: ConsultaRequest, db: Session = Depends(get_db)):
    try:
        resultados = buscar_csv_por_categoria(
            categoria=request.categoria,
            opcao=request.opcao,
            subopcao=request.subopcao,
            ano=request.ano,
            db=db
        )
        if not resultados:
            raise HTTPException(status_code=404, detail="Nenhum dado encontrado")
        return resultados
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
