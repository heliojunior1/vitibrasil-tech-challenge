from fastapi import FastAPI
from src.app.web.routes import router as main_router
from src.app.web.routes_auth import router as auth_router
from src.app.config.database import Base, engine
from src.app.models.user import User
from src.app.models.viticulture import Viticultura
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s"
)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Vitivinicultura API")

app.include_router(main_router, prefix="/api")
app.include_router(auth_router, prefix="/auth")