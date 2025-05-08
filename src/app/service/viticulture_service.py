from sqlalchemy.orm import Session
from src.app.domain.viticulture import ViticultureCategory
from src.app.repository.viticulture_repo import RepositorioViticulture
from fastapi import HTTPException
import logging

from src.app.scraper.viticulture_scraper import (
    buscar_csv_por_categoria,
    obter_subopcoes,
    obter_intervalo_anos,
    CATEGORIAS
)
logging.basicConfig(level=logging.INFO)


def consultar_dados_com_parametros(categoria, tipo, ano, opcao, subopcao, db: Session):
    try:
        dados = buscar_csv_por_categoria(categoria, opcao, subopcao, ano, db=None)
        if not dados:
            raise Exception("Nenhum dado retornado do site.")

        repo = RepositorioViticulture(db)
        with db.begin():
            for dto in dados:
                repo.adicionar(dto)

        return dados

    except Exception:
        repo = RepositorioViticulture(db)
        fallback = repo.buscar_por_categoria_tipo_ano(categoria, tipo, ano)
        if not fallback:
            raise HTTPException(status_code=500, detail="Falha ao consultar e nenhum dado no banco.")
        return fallback

def consultar_tudo(db: Session):
    logging.info("Iniciando consulta completa...")

    total_importados = 0
    registros_fallback = 0

    for cat_str, opcao in CATEGORIAS.items():
        categoria = ViticultureCategory(cat_str)
        subopcoes = obter_subopcoes(opcao)

        if not subopcoes:  # Caso como produção que não tem subopções
            subopcoes = [None]

        for subopcao in subopcoes:
            anos = obter_intervalo_anos(opcao, subopcao)
            for ano in anos:
                try:
                    dados = buscar_csv_por_categoria(categoria, opcao, subopcao, ano, db=None)
                    if not dados:
                        raise Exception("Nenhum dado do site")

                    repo = RepositorioViticulture(db)
                    with db.begin():
                        for dto in dados:
                            repo.adicionar(dto)
                    total_importados += len(dados)

                except Exception:
                    repo = RepositorioViticulture(db)
                    fallback = repo.buscar_por_categoria_tipo_ano(categoria, subopcao or "", ano)
                    if fallback:
                        registros_fallback += len(fallback)

    return {
        "status": "ok",
        "total_registros_importados": total_importados,
        "registros_fallback_usados": registros_fallback
    }
