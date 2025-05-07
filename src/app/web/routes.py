from fastapi import APIRouter, Depends
from src.app.service.viticulture_service import obter_dados
from src.app.auth.dependencies import get_current_user

router = APIRouter()

@router.get("/viticultura")
def get_viticultura(user: dict = Depends(get_current_user)):
    return obter_dados()