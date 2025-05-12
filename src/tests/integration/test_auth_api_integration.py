import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.app.config.database import SessionLocal, Base, engine
from src.app.models.user import User as UserModel

# Usar o client do conftest.py

@pytest.fixture(scope="function", autouse=True)
def setup_test_database():
    """
    Fixture para criar tabelas antes de cada teste de integração de autenticação
    e limpá-las depois.
    'autouse=True' faz com que seja executado automaticamente para cada teste no módulo.
    'scope="function"' garante que é executado para cada função de teste.
    """
    Base.metadata.create_all(bind=engine) # Cria as tabelas
    yield
    Base.metadata.drop_all(bind=engine)   # Limpa as tabelas

def test_register_user_success(client: TestClient):
    response = client.post("/auth/register", json={"username": "testuser_auth", "password": "password123"})
    assert response.status_code == 200
    assert response.json() == {"msg": "Usuário criado com sucesso"}

    # Verificar no banco (opcional, mas bom para integração)
    db: Session = SessionLocal()
    user_in_db = db.query(UserModel).filter(UserModel.username == "testuser_auth").first()
    assert user_in_db is not None
    assert user_in_db.username == "testuser_auth"
    db.close()

def test_register_user_already_exists(client: TestClient):
    # Primeiro registro
    client.post("/auth/register", json={"username": "existinguser", "password": "password123"})
    
    # Tenta registrar novamente
    response = client.post("/auth/register", json={"username": "existinguser", "password": "password456"})
    assert response.status_code == 400
    assert "Usuário já existe" in response.json()["detail"]

def test_login_user_success(client: TestClient):
    # Registrar primeiro
    username = "loginuser"
    password = "loginpassword"
    client.post("/auth/register", json={"username": username, "password": password})

    # Tentar login
    login_data = {"username": username, "password": password}
    response = client.post("/auth/login", data=login_data) # OAuth2PasswordRequestForm usa data, não json
    
    assert response.status_code == 200
    response_data = response.json()
    assert "access_token" in response_data
    assert response_data["token_type"] == "bearer"

def test_login_user_invalid_username(client: TestClient):
    login_data = {"username": "nonexistentuser", "password": "password123"}
    response = client.post("/auth/login", data=login_data)
    assert response.status_code == 401
    assert "Credenciais inválidas" in response.json()["detail"]

def test_login_user_invalid_password(client: TestClient):
    username = "user_wrong_pass"
    password = "correctpassword"
    client.post("/auth/register", json={"username": username, "password": password})

    login_data = {"username": username, "password": "wrongpassword"}
    response = client.post("/auth/login", data=login_data)
    assert response.status_code == 401
    assert "Credenciais inválidas" in response.json()["detail"]