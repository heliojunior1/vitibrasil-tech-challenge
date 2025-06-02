# app.py (no diretório raiz do seu projeto)
import sys
import os

# Adiciona o diretório 'src' ao PYTHONPATH
# Assume que 'app.py' está no mesmo nível de 'src'
sys.path.append(os.path.join(os.path.dirname(__file__)))

# Agora, importe seu arquivo principal Streamlit de src/
# Certifique-se de que main.py é um arquivo Streamlit,
# não um arquivo FastAPI puro.
# Se main.py for um Streamlit, você não pode ter chamadas FastAPI aqui,
# a menos que o FastAPI esteja embutido dentro de uma função Streamlit.
import src.app.web.main