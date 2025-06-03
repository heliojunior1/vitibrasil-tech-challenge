from fastapi import APIRouter, HTTPException, status, Depends, BackgroundTasks
from sqlalchemy.orm import Session 
from typing import List, Dict # <--- Adicionar Dict
from src.app.service.viticulture_service import obter_dados_viticultura_e_salvar
from src.app.domain.viticulture import ViticulturaListResponse 
from src.app.config.database import get_db 
from src.app.auth.dependencies import get_current_user 
from src.app.domain.viticulture import DadosEspecificosRequest
from src.app.service.viticulture_service import buscar_dados_especificos
from src.app.domain.prediction import PredictionRequest, PredictionResponse
from src.app.service.prediction_service import prediction_service


# from src.app.domain.user import User # <--- REMOVER OU COMENTAR ESTA LINHA
import logging
from fastapi import Query
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
                "imediatamente e inicia o salvamento no banco de dados em background. \n"
                "Se a raspagem ao vivo falhar, serve os últimos dados do cache do banco de dados. \n"
                "Se ambos falharem, retorna um erro. Requer token JWT válido.\n"
                "Parâmetros de paginação: offset (número de registros a pular) e limit (número máximo de registros a retornar).\n"
                "O parâmetro offset deve ser >= 0 e limit deve ser >= 1. "
            )
           )
async def get_viticulture_data_and_save(
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: Dict = Depends(get_current_user),
    offset: int = Query(default=0, ge=0, description="Número de registros a pular para paginação"),
    limit: int = Query(default=None, ge=1, description="Número máximo de registros a retornar")
):
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
        
        # Paginação dos dados
        if resultado.dados is not None and (offset >= 0 or limit is not None):
            dados_paginados = resultado.dados[offset: offset + limit if limit is not None else None]
            resultado.dados = dados_paginados

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
        "Permite ao usuário especificar um intervalo de anos e uma opção (aba) para obter dados de viticultura. \n"
        "Tenta raspagem ao vivo da Embrapa; se falhar, retorna dados do cache do banco de dados. \n"
        "O salvamento dos dados raspados ocorre em background. Requer token JWT válido.\n"
        "Opções disponíveis: 'producao', 'processamento', 'comercializacao', 'importacao', 'exportacao'\n"
        "Parâmetros de paginação: offset (número de registros a pular) e limit (número máximo de registros a retornar).\n"
        "O parâmetro offset deve ser >= 0 e limit deve ser >= 1. "
    )
)
async def obter_dados_especificos(
    request: DadosEspecificosRequest,
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: Dict = Depends(get_current_user),
    offset: int = Query(default=0, ge=0, description="Número de registros a pular para paginação"),
    limit: int = Query(default=None, ge=1, description="Número máximo de registros a retornar")
):
    username = current_user.get("sub", "Usuário Desconhecido")
    logger.info(
        f">>>> ROTA /viticultura/dados-especificos CHAMADA pelo usuário: {username} "
        f"com parâmetros: ano_min={request.ano_min}, ano_max={request.ano_max}, opcao={request.opcao}, offset={offset}, limit={limit} <<<<"
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

        if resultado.dados is None:
            logger.info("Nenhum dado encontrado para os parâmetros fornecidos.")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Nenhum dado encontrado para os parâmetros fornecidos."
            )
        # Paginação dos dados
        if resultado.dados is not None and (offset >= 0 or limit is not None):
            resultado.dados = resultado.dados[offset: offset + limit if limit is not None else None]

        return resultado

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Erro inesperado na rota /viticultura/dados-especificos: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor ao processar a solicitação. Detalhe: {str(e)}"
        )
        

@router.post("/predict", 
             response_model=PredictionResponse,
             summary="Realiza previsão de quantidade total para o ano seguinte, conforme a opção escolhida"
)
def predict_production(
    request: PredictionRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Realiza previsão de quantidade total para o ano seguinte, conforme a opção escolhida.
    Utiliza os dados armazenado na base de cache da aplicação.
    
    Pré-requisito:
    Executar um dos serviços de obtenção de dados (/dados ou /dados-especificos).
    Precisa que o ano inicial passado seja, pelo menos, 2 anos anteriores ao maior ano disponível no cache.
        
    Retorno:
        dict: Um dicionário com os seguintes campos:
            - opcao (str): Opção escolhida para a previsão (ex: 'producao', 'comercializacao').
            - ano_anterior (int): Ano mais recente anterior ao previsto que consta no cache.
            - quantidade_ano_anterior (float): Quantidade total do ano anterior ao ano de previsão.
            - ano_previsto (int): Ano para o qual a previsão foi realizada.
            - quantidade_prevista (float): Quantidade prevista para o ano previsto.
            - unidade (str): Unidade de medida da quantidade (ex: 'L').
            - confianca (float): Grau de confiança da previsão (ex: 0.75).
            - modelo_usado (str): Nome do modelo utilizado na previsão (ex: 'Prophet').
            - dados_historicos_anos (int): Quantidade de anos da série histórica usada para previsão.
            - data_previsao (str): Data e hora em que a previsão foi realizada (ISO 8601).
            - detalhes (dict): Dicionário com detalhes adicionais da previsão:
                - mae (float | None): Mean Absolute Error.
                - rmse (float | None): Root Mean Squared Error.
                - trend (str): Tendência identificada nos dados (ex: 'crescente').
                - variacao_percentual (float): Variação percentual prevista em relação ao ano anterior.    """
    try:
        prediction = prediction_service.predict_production(db, request)
        return prediction
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno na previsão: {str(e)}")

@router.get("/opcoes",
            summary="Retorna as opções de agrupamento de dados disponíveis no site da Embrapa"
)
def get_available_options(current_user: dict = Depends(get_current_user)):
    """
    Retorna as opções de agrupamento de dados disponíveis no site da Embrapa para utilizar no serviço de previsão. 
    Utiliza os dados armazenado na base de cache da aplicação.
    
    Pré-requisito: executar um dos servi;os de obtenção de dados (/dados ou /dados-especificos).
    """
    return {
        "opcoes_disponiveis": prediction_service.supported_options,
        "exemplo_uso": {
            "opcao": "producao",
            "ano_minimo": 2010
        },
        "descricao": "O serviço retorna a quantidade total do ano anterior e a previsão para o próximo ano"
    }