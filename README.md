# Vitibrasil Tech Challenge API

Projeto de API para coleta e consulta de dados de vitivinicultura da Embrapa. Desenvolvido como parte da especialização em Machine Learning Engineering, utilizando FastAPI para a construção da API e `requests` com `BeautifulSoup` para a raspagem de dados.

## Funcionalidades

*   **Coleta de Dados:** Raspagem de dados atualizados do site Vitibrasil da Embrapa.
*   **Armazenamento em Cache:** Os dados raspados são armazenados em um banco de dados SQLite para acesso rápido e como fallback em caso de falha na raspagem ao vivo.
*   **Autenticação:** Proteção dos endpoints de dados utilizando autenticação JWT (registro e login de usuários).
*   **Processamento em Background:** O salvamento dos dados no banco de dados após a raspagem é realizado em background para não bloquear a resposta da API.
*   **Estrutura Organizada:** O projeto segue uma estrutura modular para facilitar a manutenção e escalabilidade.

## Tech Stack

*   **Backend:** FastAPI
*   **Raspagem de Dados:** `requests`, `BeautifulSoup4`, `lxml`
*   **Banco de Dados:** SQLAlchemy, SQLite
*   **Validação de Dados:** Pydantic
*   **Autenticação:** `python-jose[cryptography]`, `passlib[bcrypt]`
*   **Servidor ASGI:** Uvicorn
*   **Servidor WSGI (Produção):** Gunicorn
*   **Gerenciamento de Dependências:** pip
*   **Variáveis de Ambiente:** `python-dotenv`, `pydantic-settings`

## Estrutura do Projeto

```
vitibrasil-tech-challenge/
├── src/
│   ├── app/
│   │   ├── auth/         # Lógica de autenticação e JWT
│   │   ├── config/       # Configurações de banco de dados e app
│   │   ├── domain/       # Modelos Pydantic para validação e serialização
│   │   ├── models/       # Modelos SQLAlchemy para o ORM
│   │   ├── repository/   # Camada de acesso aos dados (operações de BD)
│   │   ├── scraper/      # Lógica de raspagem de dados
│   │   ├── service/      # Lógica de negócios
│   │   ├── utils/        # Utilitários (ex: hash de senha)
│   │   └── web/          # Definição da aplicação FastAPI e rotas
│   │       ├── main.py   # Ponto de entrada da aplicação FastAPI
│   │       ├── routes.py # Rotas principais da API
│   │       └── routes_auth.py # Rotas de autenticação
│   ├── tests/            # Testes unitários e de integração (a serem desenvolvidos)
├── .env.example          # Arquivo de exemplo para variáveis de ambiente
├── .gitignore
├── LICENSE
├── README.md
├── render.yaml           # Configuração para deploy no Render
└── requirements.txt      # Dependências do projeto
```

## Configuração e Instalação

### Pré-requisitos

*   Python 3.8 ou superior
*   pip

### Passos

1.  **Clone o repositório:**
    ```bash
    git clone https://github.com/seu-usuario/vitibrasil-tech-challenge.git
    cd vitibrasil-tech-challenge
    ```

2.  **Crie e ative um ambiente virtual:**
    ```bash
    python -m venv venv
    ```
    *   No Windows (PowerShell):
        ```powershell
        .\venv\Scripts\Activate.ps1
        ```
    *   No macOS/Linux:
        ```bash
        source venv/bin/activate
        ```

3.  **Instale as dependências:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure as variáveis de ambiente:**
    Crie um arquivo `.env` na raiz do projeto, baseado no arquivo `.env.example` (se fornecido) ou adicione as seguintes variáveis. Para este projeto, a URL do banco de dados é definida diretamente no código ([`src/app/config/database.py`](src\app\config\database.py)), mas a chave secreta JWT é importante para produção.
    ```env
    # .env
    # Nenhuma variável de ambiente é estritamente necessária para rodar localmente
    # com SQLite e a SECRET_KEY padrão em jwt_handler.py.
    # Para produção, você configuraria DATABASE_URL e JWT_SECRET via variáveis de ambiente do host.
    ```
    A `SECRET_KEY` para JWT está definida em [`src/app/auth/jwt_handler.py`](src\app\auth\jwt_handler.py) e pode ser externalizada para uma variável de ambiente para maior segurança em produção.

## Executando a Aplicação

### Servidor de Desenvolvimento (Uvicorn)

Para rodar a aplicação em modo de desenvolvimento com recarregamento automático:
```bash
uvicorn src.app.web.main:app --reload
```
A API estará disponível em `http://127.0.0.1:8000`.
A documentação interativa (Swagger UI) estará em `http://127.0.0.1:8000/docs`.

### Servidor de Produção (Gunicorn)

Para um ambiente de produção, você pode usar Gunicorn (conforme configurado em [`render.yaml`](render.yaml)):
```bash
gunicorn src.app.web.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```
(A porta `$PORT` será definida pelo ambiente de hospedagem como o Render).

## Endpoints da API

Todos os endpoints de dados estão prefixados com `/api`. Endpoints de autenticação estão prefixados com `/auth`.

### Autenticação

*   **`POST /auth/register`**: Registra um novo usuário.
    *   Corpo da Requisição:
        ```json
        {
          "username": "testuser",
          "password": "password123"
        }
        ```
*   **`POST /auth/login`**: Autentica um usuário e retorna um token JWT.
    *   Corpo da Requisição (form data): `username` e `password`.

### Viticultura

*   **`GET /api/viticultura/dados`**: (Requer Autenticação) Obtém os dados de viticultura.
    *   Tenta buscar os dados mais recentes da Embrapa.
    *   Se a raspagem ao vivo falhar, serve os últimos dados do cache do banco de dados.
    *   O salvamento no banco de dados ocorre em background.
    *   Header de Autorização: `Bearer <seu_token_jwt>`

## Deploy

Este projeto inclui um arquivo [`render.yaml`](render.yaml) para facilitar o deploy na plataforma [Render](https://render.com/).

## Licença

Este projeto está licenciado sob a Licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.