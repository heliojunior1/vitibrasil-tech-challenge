from fastapi import FastAPI
from app.web.routes import router

app = FastAPI(title="Vitivinicultura API")

app.include_router(router)