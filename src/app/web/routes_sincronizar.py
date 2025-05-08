from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.app.config.database import get_db
from src.app.scraper.viticulture_scraper import buscar_csv_por_categoria
from src.app.domain.viticulture import ViticultureCategory

router = APIRouter(prefix="/viticulture", tags=["Viticulture"])

# Configuração dos parâmetros disponíveis
CATEGORIAS = {
    "producao": "opt_02",
    "processamento": "opt_03",
    "comercializacao": "opt_04",
    "importacao": "opt_05",
    "exportacao": "opt_06"
}

TIPOS = ["subopt_01", "subopt_02", "subopt_03", "subopt_04", "subopt_05"]

ANOS = list(range(2018, 2025))

@router.post("/sincronizar")
def sincronizar_dados(db: Session = Depends(get_db)):
    total = 0
    for cat_str, opcao in CATEGORIAS.items():
        categoria = ViticultureCategory(cat_str)
        for tipo in TIPOS:
            for ano in ANOS:
                print(f"Sincronizando {cat_str} - {tipo} - {ano}")
                try:
                    registros = buscar_csv_por_categoria(categoria, opcao, tipo, ano, db)
                    total += len(registros)
                except Exception as e:
                    print(f"Erro em {cat_str}-{tipo}-{ano}: {e}")
    return {"status": "ok", "total_registros_importados": total}
