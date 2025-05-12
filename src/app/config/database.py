from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from .settings import settings # Importa a instância 'settings' configurada

# Obtém a URL do banco de dados a partir do objeto settings.
# 'settings' já terá carregado a DATABASE_URL de variáveis de ambiente ou do .env.
DB_URL_FROM_SETTINGS = settings.DATABASE_URL

engine_args = {}
# Adiciona connect_args específico para SQLite.
# Para PostgreSQL ou outros bancos, esses argumentos não são necessários ou podem ser diferentes.
if DB_URL_FROM_SETTINGS.startswith("sqlite"):
    engine_args["connect_args"] = {"check_same_thread": False}

# Cria a engine do SQLAlchemy usando a URL e quaisquer argumentos específicos.
engine = create_engine(DB_URL_FROM_SETTINGS, **engine_args)

# Cria uma fábrica de sessões (SessionLocal) que será usada para criar sessões de banco de dados.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para as classes de modelo declarativas do SQLAlchemy.
Base = declarative_base()

def get_db():
    """
    Função de dependência do FastAPI para obter uma sessão de banco de dados.
    Garante que a sessão seja fechada após o uso.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()