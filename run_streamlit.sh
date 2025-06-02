# run_streamlit.sh
#!/bin/bash

# Adiciona o diretório raiz do projeto ao PYTHONPATH
# Este script deve estar no diretório raiz do seu projeto
export PYTHONPATH=$PYTHONPATH:$(pwd)

# Executa o aplicativo Streamlit
streamlit run src/app/web/main.py --server.port $PORT --server.enableCORS false --server.enableXsrfProtection false