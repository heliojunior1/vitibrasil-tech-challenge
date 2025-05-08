from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from src.app.config.database import get_db
from src.app.schemas.viticultura_dto import ViticulturaDTO
from src.app.repository.viticulture_repo import RepositorioViticulture

router = APIRouter(prefix="/viticulture", tags=["Viticulture"])

@router.post("/", response_model=ViticulturaDTO) 
def criar_viticultura(dto: ViticulturaDTO, db: Session = Depends(get_db)):
    repo = RepositorioViticulture(db)
    try:
        return repo.adicionar(dto)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=List[ViticulturaDTO])
def listar_viticultura(db: Session = Depends(get_db)):
    repo = RepositorioViticulture(db)
    return repo.listar_todos()

@router.post("/viticulture/scrape")
def iniciar_scraping(db: Session = Depends(get_db)):
    url = "http://vitibrasil.cnpuv.embrapa.br/"
    extrair_csvs_e_salvar(url, ViticultureCategory.producao, db)
    return {"status": "Scraping iniciado com sucesso"}