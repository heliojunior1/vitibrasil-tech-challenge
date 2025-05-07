# vitibrasil-tech-challenge
Projeto da API para coleta e consulta de dados da Embrapa usando FastAPI + Selenium para a especialização de  Machine Learning Engineering


python -m venv venv 
 .\venv\Scripts\Activate.ps1
$env:DATABASE_URL = "sqlite:///./viticultura.db"

pip install -r requirements.txt
uvicorn src.app.web.main:app --reload
