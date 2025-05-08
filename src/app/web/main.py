from fastapi import FastAPI
from src.app.web.routes import router as main_router
from src.app.web.routes_auth import router as auth_router
from src.app.web.routes_consulta import router as routes_consulta
from src.app.web.routes_sincronizar import router as routes_sincronizar

from src.app.config.database import Base, engine
from src.app.models.user import User
from src.app.models.viticulture import Viticultura

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Vitivinicultura API")

# Rotas principais
app.include_router(main_router, prefix="/api")
app.include_router(auth_router, prefix="/auth")
app.include_router(routes_consulta, prefix="/api")
app.include_router(routes_sincronizar, prefix="/api")c