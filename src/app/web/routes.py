from fastapi import APIRouter, HTTPException, status, Depends, BackgroundTasks
from sqlalchemy.orm import Session 
from typing import List, Dict # <--- Adicionar Dict
from src.app.service.viticulture_service import obter_dados_viticultura_e_salvar
from src.app.domain.viticulture import ViticulturaListResponse 
from src.app.config.database import get_db 
from src.app.auth.dependencies import get_current_user 
from src.app.domain.viticulture import DadosEspecificosRequest
from src.app.service.viticulture_service import buscar_dados_especificos


# from src.app.domain.user import User # <--- REMOVER OU COMENTAR ESTA LINHA
import logging
logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/viticultura",
    tags=["Viticultura"],
    responses={
        503: {"description": "Serviço indisponível (falha na raspagem e no cache do BD)"},
        500: {"description": "Erro interno do servidor"},
        401: {"description": "Não autorizado"}
    }
)

@router.get("/dados", 
            response_model=ViticulturaListResponse,
            summary="Obtém ou atualiza e obtém dados de viticultura da Embrapa (Requer Autenticação)",
            description=(
                "Tenta obter os dados mais recentes da Embrapa. Se sucesso, retorna os dados "
                "imediatamente e inicia o salvamento no banco de dados em background. "
                "Se a raspagem ao vivo falhar, serve os últimos dados do cache do banco de dados. "
                "Se ambos falharem, retorna um erro. Requer token JWT válido."
            )
           )
async def get_viticulture_data_and_save(
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: Dict = Depends(get_current_user) # <--- Alterar tipo para Dict
):
    # Ajustar o log para usar .get() com segurança, assumindo que 'sub' é o username no payload
    username = current_user.get("sub", "Usuário Desconhecido")
    logger.info(f">>>> ROTA /viticultura/dados CHAMADA pelo usuário: {username} <<<<")
    try:
        resultado: ViticulturaListResponse = obter_dados_viticultura_e_salvar(
            db=db, background_tasks=background_tasks 
        ) 
        
        if not resultado.dados and "Falha" in resultado.fonte:
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            if "Erro ao Ler Cache do BD" in resultado.fonte: 
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            
            raise HTTPException(
                status_code=status_code, 
                detail=resultado.message or "Não foi possível obter os dados da Embrapa nem do cache do banco de dados."
            )
        
        return resultado

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Erro inesperado na rota /viticultura/dados: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Erro interno do servidor ao processar a solicitação. Detalhe: {str(e)}"
        )
    
@router.post(
    "/dados-especificos",
    response_model=ViticulturaListResponse,
    summary="Obtém dados de viticultura por intervalo de anos e opção (Requer Autenticação)",
    description=(
        "Permite ao usuário especificar um intervalo de anos e uma opção (aba) para obter dados de viticultura. "
        "Tenta raspagem ao vivo da Embrapa; se falhar, retorna dados do cache do banco de dados. "
        "O salvamento dos dados raspados ocorre em background. Requer token JWT válido."
    )
)
async def obter_dados_especificos(
    request: DadosEspecificosRequest,
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: Dict = Depends(get_current_user)
):
    username = current_user.get("sub", "Usuário Desconhecido")
    logger.info(
        f">>>> ROTA /viticultura/dados-especificos CHAMADA pelo usuário: {username} "
        f"com parâmetros: ano_min={request.ano_min}, ano_max={request.ano_max}, opcao={request.opcao} <<<<"
    )
    try:
        resultado: ViticulturaListResponse = buscar_dados_especificos(
            db=db,
            background_tasks=background_tasks,
            ano_min=request.ano_min,
            ano_max=request.ano_max,
            opcao=request.opcao
        )

        if not resultado.dados and "Falha" in resultado.fonte:
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            if "Cache do BD Vazio" in resultado.fonte:
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

            raise HTTPException(
                status_code=status_code,
                detail=resultado.message or "Não foi possível obter os dados da Embrapa nem do cache do banco de dados."
            )

        return resultado

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Erro inesperado na rota /viticultura/dados-especificos: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor ao processar a solicitação. Detalhe: {str(e)}"
        )