from fastapi import APIRouter, HTTPException, status, Depends # Add Depends
from sqlalchemy.orm import Session # Add Session
from typing import List 

# Import the service function and Pydantic models
from src.app.service.viticulture_service import obter_dados_viticultura_e_salvar
from src.app.domain.viticulture import ViticulturaListResponse # This is the expected response model

# Import the database session dependency
from src.app.config.database import get_db_session # Assuming get_db_session is in database.py

router = APIRouter(
    prefix="/viticultura",
    tags=["Viticultura"],
    responses={
        # 404: {"description": "Não encontrado"}, # Can be more specific if needed
        503: {"description": "Serviço indisponível (falha na raspagem e no cache do BD)"},
        500: {"description": "Erro interno do servidor"}
    }
)

@router.get("/dados", 
            response_model=ViticulturaListResponse, # Use the wrapper response model
            summary="Obtém ou atualiza e obtém dados de viticultura da Embrapa",
            description=(
                "Tenta obter os dados mais recentes da Embrapa, salvando-os no banco de dados. "
                "Se a raspagem ao vivo falhar, serve os últimos dados do cache do banco de dados. "
                "Se ambos falharem, retorna um erro."
            )
           )
async def get_viticulture_data_and_save(db: Session = Depends(get_db_session)):
    """
    Endpoint para obter e opcionalmente atualizar dados de viticultura.
    - Tenta uma raspagem de dados em tempo real do site da Embrapa.
    - Se a raspagem for bem-sucedida, os dados são salvos/atualizados no banco de dados e retornados.
    - Se a raspagem falhar, tenta carregar os dados do cache do banco de dados.
    - Se tanto a raspagem quanto o cache do BD falharem, uma resposta de erro é retornada.
    """
    try:
        # obter_dados_viticultura_e_salvar is synchronous, FastAPI handles it in a thread pool
        resultado: ViticulturaListResponse = obter_dados_viticultura_e_salvar(db=db) 
        
        # Check if data retrieval was ultimately unsuccessful
        if not resultado.dados and "Falha" in resultado.fonte:
            # This means scraping failed AND DB cache was also problematic
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            # You could add more specific status codes based on resultado.message if needed
            
            raise HTTPException(
                status_code=status_code, 
                detail=resultado.message or "Não foi possível obter os dados da Embrapa nem do cache do banco de dados."
            )
        
        # If data is present (either from live scrape + save, or from DB cache)
        return resultado

    except HTTPException as e:
        # Re-raise HTTPExceptions that were already raised
        raise e
    except Exception as e:
        # Catch any other unexpected errors during the process
        # Log the exception e here for debugging on the server
        print(f"Erro inesperado na rota /viticultura/dados: {str(e)}")
        # It's good practice to rollback the session in case of an unexpected error
        # if the service layer didn't already do it, though for reads it's less critical.
        # For operations that write, this is more important.
        db.rollback() 
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Erro interno do servidor ao processar a solicitação. Detalhe: {str(e)}"
        )

# Ensure this router is included in your main FastAPI app instance (e.g., in src/app/web/main.py)