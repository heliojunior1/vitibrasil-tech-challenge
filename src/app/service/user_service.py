from sqlalchemy.orm import Session
from src.app.domain.user import UserCreate
from src.app.repository.user_repo import get_user_by_username, create_user
from src.app.utils.password_utils import hash_password, verify_password

def register_user(db: Session, user_data: UserCreate):
    if get_user_by_username(db, user_data.username):
        raise ValueError("Usuário já existe")
    hashed_password = hash_password(user_data.password)
    return create_user(db, user_data.username, hashed_password)

def authenticate_user(db: Session, username: str, password: str):
    user = get_user_by_username(db, username)
    if not user or not verify_password(password, user.password):
        return None
    return user