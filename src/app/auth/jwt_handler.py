from datetime import datetime, timedelta
from jose import JWTError, jwt
import os # Adicionar import os

# SECRET_KEY = "supersecretkey" # Remover ou comentar esta linha
# Usar uma variável de ambiente para a SECRET_KEY, com um fallback para desenvolvimento
SECRET_KEY = os.getenv("JWT_SECRET", "supersecretkey_para_desenvolvimento_local_se_nao_definido")
ALGORITHM = "HS256"
EXPIRE_MINUTES = 60

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None