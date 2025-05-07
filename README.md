# vitibrasil-tech-challenge
Projeto da API para coleta e consulta de dados da Embrapa usando FastAPI + Selenium para a especialização de  Machine Learning Engineering

# comandos para serem executados
python -m venv venv 
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn src.app.web.main:app --reload
