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
│   │   ├── auth/                   # Lógica de autenticação e JWT
│   │   ├── config/                 # Configurações de banco de dados e app
│   │   ├── domain/                 # Modelos Pydantic para validação e serialização
│   │   ├── models/                 # Modelos SQLAlchemy para o ORM
│   │   ├── repository/             # Camada de acesso aos dados (operações de BD)
│   │   ├── scraper/                # Lógica de raspagem de dados
│   │   ├── service/                # Lógica de negócios
│   │   ├── utils/                  # Utilitários (ex: hash de senha)
│   │   └── web/                    # Definição da aplicação FastAPI e rotas
│   │       ├── main.py             # Ponto de entrada da aplicação FastAPI
│   │       ├── routes.py           # Rotas principais da API
│   │       └── routes_auth.py      # Rotas de autenticação
│   ├── tests/                      # Testes unitários e de integração (a serem desenvolvidos)
│   ├── architecture-diagram.drawio # Diagrama de arquitetura ("Draw.io Integration" - Extensão do VS Code)
├── .env.example                    # Arquivo de exemplo para variáveis de ambiente
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
    git clone https://github.com/heliojunior1/vitibrasil-tech-challenge.git
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
    Crie um arquivo `.env` na raiz do projeto, baseado no arquivo `.env.example` ou adicione as seguintes variáveis (exemplo):
    ```env
    # .env
    # Para funcionamento local, as seguintes variáveis são obrigatórias:
    # DATABASE_URL - Define a URL do banco de dados (SQLite para desenvolvimento)
    # JWT_SECRET - Chave secreta para geração de tokens JWT
    ```
    **Importante:** Ambas as variáveis são obrigatórias para o funcionamento da aplicação, mesmo em desenvolvimento local.

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

## Executando a aplicação com Docker

Você pode rodar a API do Vitibrasil Tech Challenge utilizando Docker. Siga os passos abaixo.

### Pré-requisito

- Docker instalado em sua máquina.  
Se ainda não tem o Docker instalado, siga as instruções oficiais de instalação no site:  
[Como instalar o Docker](https://docs.docker.com/get-docker/)

### 1. Build da imagem Docker

Na raiz do projeto, execute:

```sh
docker build -f docker/Dockerfile -t vitibrasil-api .
```

### 2. Rodando o container

Execute o container (usar o nome `vitibrasil-api` é opcional), expondo a porta 8080e passando as variáveis de ambiente através do arquivo `.env`:

```sh
docker run --name vitibrasil-api --env-file .env -p 8080:8080 vitibrasil-api
```

A aplicação estará disponível em [http://localhost:8080](http://localhost:8080).

---

**Observações:**
- Certifique-se de que o arquivo `.env` esteja presente e contendo as variáveis de ambiente necessárias.
- Para rodar em modo "detached" (em segundo plano), adicione o parâmetro `-d` ao comando `docker run`.

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



*   **`POST /api/viticultura/dados-especificos`**: (Requer Autenticação) Obtém dados de viticultura para um intervalo de anos e uma opção (aba).
    *   Permite ao usuário especificar o intervalo de anos e a aba desejada.
    *   Tenta raspagem ao vivo da Embrapa; se falhar, retorna dados do cache do banco de dados.
    *   O salvamento dos dados raspados ocorre em background.
    *   Header de Autorização: `Bearer <seu_token_jwt>`
    *   Corpo da requisição (JSON):
        ```json
        {
          "ano_min": 2022,
          "ano_max": 2023,
          "opcao": "producao"
        }
        ```
    *   Resposta (exemplo):
        ```json
        {
          "fonte": "Embrapa (Raspagem Específica - Salvamento em Andamento)",
          "dados": [
            {
              "id": null,
              "ano": 2022,
              "aba": "producao",
              "subopcao": "vinhos_de_mesa",
              "dados": [
                {"produto": "Vinho Tinto", "quantidade": 1000, "unidade_quantidade": "L"}
              ],
              "data_raspagem": "2024-05-15T12:34:56.789Z"
            }
          ],
          "message": "Dados de raspagem (2022-2023, producao) retornados. Salvamento no banco de dados iniciado em background."
        }
        ```


## Deploy


Este projeto inclui um arquivo [`render.yaml`](render.yaml) para facilitar o deploy na plataforma [Render](https://render.com/).


A criacao é feito no render. Precisar adicionar as variaveis JWT_SECRET e DATABASE_URL 


**Nota para Desenvolvimento Local:**

Se você clonar este projeto para desenvolvimento local, precisará criar um arquivo chamado `.env` na raiz do projeto. Este arquivo não é versionado no Git (e está incluído no `.gitignore`) por razões de segurança e para permitir configurações específicas do ambiente.

O arquivo `.env` deve conter as seguintes variáveis (ajuste os valores conforme necessário para o seu ambiente local):

```env
DATABASE_URL="sqlite:///./viticultura.db"
JWT_SECRET="coloque_aqui_um_segredo_jwt_bem_forte_para_desenvolvimento"
```

Sem este arquivo `.env` configurado corretamente, a aplicação pode não iniciar localmente devido à ausência das variáveis de ambiente `DATABASE_URL` e `JWT_SECRET` que são esperadas pelo arquivo `src/app/config/settings.py`.

## Realizar testes
python -m pytest



## Licença

Este projeto está licenciado sob a Licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.
