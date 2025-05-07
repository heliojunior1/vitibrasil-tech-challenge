from fastapi import FastAPI
from src.app.web.routes import router

app = FastAPI(title="Vitivinicultura API")

app.include_router(router)