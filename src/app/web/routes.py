from fastapi import APIRouter
from app.service.viticulture_service import obter_dados

router = APIRouter()

@router.get("/viticultura")
def get_viticultura():
    return obter_dados()