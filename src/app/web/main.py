from fastapi import FastAPI
from src.app.web.routes_viticulture import router as main_router
from src.app.web.routes_auth import router as auth_router
from src.app.web.routes_viticulture import router as viticulture_router  # ⬅️ Adicionado

from src.app.config.database import Base, engine
from src.app.models.user import User
from src.app.models.viticulture import Viticulture

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Vitivinicultura API")

app.include_router(auth_router, prefix="/auth")
app.include_router(viticulture_router, prefix="/api")