import pytest
from unittest.mock import MagicMock
from sqlalchemy.orm import Session
from src.app.repository import user_repo
from src.app.models.user import User as UserModel

@pytest.fixture
def mock_db_session():
    return MagicMock(spec=Session)

def test_get_user_by_username_found(mock_db_session):
    mock_user = UserModel(id=1, username="testuser", password="hashedpassword")
    mock_db_session.query(UserModel).filter(UserModel.username == "testuser").first.return_value = mock_user

    user = user_repo.get_user_by_username(mock_db_session, "testuser")

    mock_db_session.query(UserModel).filter(UserModel.username == "testuser").first.assert_called_once()
    assert user is not None
    assert user.username == "testuser"

def test_get_user_by_username_not_found(mock_db_session):
    mock_db_session.query(UserModel).filter(UserModel.username == "nonexistent").first.return_value = None

    user = user_repo.get_user_by_username(mock_db_session, "nonexistent")

    mock_db_session.query(UserModel).filter(UserModel.username == "nonexistent").first.assert_called_once()
    assert user is None

def test_create_user(mock_db_session):
    username = "newuser"
    hashed_password = "newhashedpassword"

    # Mock para o objeto User que seria criado e para o db.refresh
    # A forma como o user_repo.create_user é escrito, ele cria o User internamente.
    # Podemos verificar as chamadas ao db.
    
    created_user = user_repo.create_user(mock_db_session, username, hashed_password)

    # Verificar se db.add foi chamado com um objeto User com os dados corretos
    # Acessar o argumento com o qual mock_db_session.add foi chamado
    args_add, _ = mock_db_session.add.call_args
    user_object_added = args_add[0]

    assert isinstance(user_object_added, UserModel)
    assert user_object_added.username == username
    assert user_object_added.password == hashed_password
    
    mock_db_session.add.assert_called_once_with(user_object_added)
    mock_db_session.commit.assert_called_once()
    mock_db_session.refresh.assert_called_once_with(user_object_added)
    
    # O user retornado deve ser o objeto que foi "refrescado"
    assert created_user == user_object_added