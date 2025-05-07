from fastapi import FastAPI
from src.app.web.routes import router as main_router
from src.app.web.routes_auth import router as auth_router

app = FastAPI(title="Vitivinicultura API")

app.include_router(main_router)
app.include_router(auth_router)