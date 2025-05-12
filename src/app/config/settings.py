from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os

# Carrega as variáveis do arquivo .env para o ambiente,
# permitindo que BaseSettings as encontre.
# Isso é útil para desenvolvimento local.
load_dotenv()

class Settings(BaseSettings):
    """
    Configurações da aplicação carregadas de variáveis de ambiente ou de um arquivo .env.
    """
    DATABASE_URL: str  # Obrigatório: URL de conexão com o banco de dados
    JWT_SECRET: str    # Obrigatório: Chave secreta para JWT

    # Configurações opcionais com valores padrão, se necessário:
    # API_V1_STR: str = "/api/v1"
    # PROJECT_NAME: str = "Vitibrasil API"

    class Config:
        # O Pydantic tentará carregar variáveis de um arquivo .env se ele existir.
        # A chamada load_dotenv() acima garante que as variáveis de ambiente
        # sejam carregadas antes da inicialização de Settings.
        env_file = ".env"
        env_file_encoding = 'utf-8'
        extra = 'ignore' # Ignora variáveis de ambiente extras que não estão definidas na classe Settings

# Cria uma instância única das configurações para ser usada em toda a aplicação.
# Se DATABASE_URL ou JWT_SECRET não forem encontradas (nem no ambiente nem no .env),
# Pydantic levantará um erro de validação na inicialização.
settings = Settings()

# Para depuração, você pode imprimir as configurações carregadas:
# print("Configurações carregadas:")
# print(f"  DATABASE_URL: {settings.DATABASE_URL}")
# print(f"  JWT_SECRET: {'*' * len(settings.JWT_SECRET) if settings.JWT_SECRET else None}") # Não imprima o segredo real em logs de produção