import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import datetime
from src.app.web.main import app
from src.app.auth.dependencies import get_current_user
from src.app.models.viticulture import Viticultura as ViticulturaModel
from src.app.config.database import SessionLocal, Base, engine
from src.app.service.viticulture_service import _save_data_in_background
from src.app.domain.viticulture import ViticulturaCreate

# Paths to the functions that will be mocked
PATH_RUN_FULL_SCRAPE = "src.app.service.viticulture_service.run_full_scrape"
PATH_GET_LATEST_SCRAPE_GROUP = "src.app.service.viticulture_service.get_latest_scrape_group"
PATH_BACKGROUND_TASKS_ADD_TASK = "fastapi.BackgroundTasks.add_task"
PATH_RUN_SCRAPE_BY_PARAMS = "src.app.service.viticulture_service.run_scrape_by_params"
PATH_GET_SPECIFIC_DATA_FROM_DB = "src.app.service.viticulture_service.get_specific_data_from_db"

MOCK_USER_PAYLOAD = {"sub": "testuser", "username": "testuser"}
MOCK_CACHE_TIMESTAMP = datetime.utcnow()

MOCK_CACHE_DATA_FROM_DB = [
    ViticulturaModel(
        id=1,
        ano=2023,
        aba="Produção Teste",
        subopcao="Vinhos de Mesa Teste",
        dados_list_json=[{"produto": "Vinho Tinto Teste", "quantidade": 1000, "unidade_quantidade": "L"}],
        data_raspagem=MOCK_CACHE_TIMESTAMP
    ),
    ViticulturaModel(
        id=2,
        ano=2023,
        aba="Comercialização Teste",
        subopcao=None,
        dados_list_json=[{"produto": "Suco de Uva Teste", "valor": 500.50, "unidade_valor": "US$"}],
        data_raspagem=MOCK_CACHE_TIMESTAMP
    )
]

@pytest.fixture(scope="function", autouse=True)
def setup_test_database_for_data_api():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def mock_get_current_user_override():
    return MOCK_USER_PAYLOAD

def test_get_data_live_scrape_success_triggers_background_save(client: TestClient):
    app.dependency_overrides[get_current_user] = mock_get_current_user_override
    
    current_time_scrape = datetime.utcnow()
    mock_live_scraped_data = [
        {"ano": 2024, "aba": "Produção Ao Vivo", "subopcao": "Vinhos Especiais", "dados": [{"produto": "Espumante", "quantidade": 500}]},
        {"ano": 2024, "aba": "Exportação Ao Vivo", "subopcao": None, "dados": [{"pais": "EUA", "valor": 10000}]}
    ]

    with patch("src.app.service.viticulture_service.datetime") as mock_datetime_service, \
         patch(PATH_RUN_FULL_SCRAPE) as mock_run_scrape, \
         patch(PATH_BACKGROUND_TASKS_ADD_TASK) as mock_add_task:

        mock_datetime_service.utcnow.return_value = current_time_scrape
        mock_run_scrape.return_value = mock_live_scraped_data

        response = client.get("/api/viticultura/dados")

        assert response.status_code == 200
        response_data = response.json()

        assert "Embrapa (Raspagem Ao Vivo - Salvamento em Andamento)" in response_data["fonte"]
        assert f"Dados de raspagem ao vivo ({current_time_scrape.isoformat()}) retornados." in response_data["message"]
        assert len(response_data["dados"]) == len(mock_live_scraped_data)
        
        for i, item_resp in enumerate(response_data["dados"]):
            assert item_resp["ano"] == mock_live_scraped_data[i]["ano"]
            assert item_resp["aba"] == mock_live_scraped_data[i]["aba"]
            assert item_resp["subopcao"] == mock_live_scraped_data[i].get("subopcao")
            assert item_resp["dados"] == mock_live_scraped_data[i]["dados"]
            assert item_resp["data_raspagem"] == current_time_scrape.isoformat()
            assert item_resp["id"] is None

        mock_add_task.assert_called_once()
        args_call_add_task, _ = mock_add_task.call_args
        
        assert args_call_add_task[0] == _save_data_in_background
        
        data_passed_to_bg = args_call_add_task[1]
        assert len(data_passed_to_bg) == len(mock_live_scraped_data)
        for i, vc_item in enumerate(data_passed_to_bg):
            assert isinstance(vc_item, ViticulturaCreate)
            assert vc_item.ano == mock_live_scraped_data[i]["ano"]
            assert vc_item.aba == mock_live_scraped_data[i]["aba"]
            assert vc_item.subopcao == mock_live_scraped_data[i].get("subopcao")
            assert vc_item.dados == mock_live_scraped_data[i]["dados"]
            assert vc_item.data_raspagem == current_time_scrape

    del app.dependency_overrides[get_current_user]

def test_get_data_from_cache_when_scrape_fails(client: TestClient):
    app.dependency_overrides[get_current_user] = mock_get_current_user_override

    with patch(PATH_RUN_FULL_SCRAPE) as mock_scrape, \
         patch(PATH_GET_LATEST_SCRAPE_GROUP) as mock_get_cache:

        mock_scrape.return_value = [] 
        mock_get_cache.return_value = MOCK_CACHE_DATA_FROM_DB

        response = client.get("/api/viticultura/dados")

        assert response.status_code == 200
        response_data = response.json()

        expected_msg_cache_part = "Raspagem ao vivo não retornou dados"
        latest_db_timestamp_str = MOCK_CACHE_TIMESTAMP.isoformat()
        
        expected_fonte = f"Cache (Banco de Dados - Raspagem de {latest_db_timestamp_str}) (após: {expected_msg_cache_part})"
        expected_message = f"{expected_msg_cache_part}. Usando cache do BD se disponível."
        
        assert response_data["fonte"] == expected_fonte
        assert response_data["message"] == expected_message
        assert len(response_data["dados"]) == len(MOCK_CACHE_DATA_FROM_DB)

        for i, expected_item_model in enumerate(MOCK_CACHE_DATA_FROM_DB):
            actual_item_response = response_data["dados"][i]
            assert actual_item_response["id"] == expected_item_model.id
            assert actual_item_response["ano"] == expected_item_model.ano
            assert actual_item_response["aba"] == expected_item_model.aba
            assert actual_item_response["subopcao"] == expected_item_model.subopcao
            assert actual_item_response["dados"] == expected_item_model.dados_list_json
            assert actual_item_response["data_raspagem"] == expected_item_model.data_raspagem.isoformat()

    del app.dependency_overrides[get_current_user]

def test_get_data_fails_when_scrape_and_cache_fail(client: TestClient):
    app.dependency_overrides[get_current_user] = mock_get_current_user_override

    with patch(PATH_RUN_FULL_SCRAPE) as mock_scrape, \
         patch(PATH_GET_LATEST_SCRAPE_GROUP) as mock_get_cache:

        mock_scrape.return_value = []
        mock_get_cache.return_value = []

        response = client.get("/api/viticultura/dados")

        assert response.status_code == 503
        response_data = response.json()
        assert "Raspagem ao vivo não retornou dados. Usando cache do BD se disponível. Cache do BD também está vazio." in response_data["detail"]

    del app.dependency_overrides[get_current_user]

def test_get_data_from_real_db_when_scrape_fails(client: TestClient):
    app.dependency_overrides[get_current_user] = mock_get_current_user_override

    db_session_for_setup = SessionLocal()
    test_timestamp = datetime.utcnow()
    
    real_db_data_to_insert = [
        ViticulturaModel(
            ano=2025, 
            aba="Teste Real DB", 
            subopcao="Sub Teste Real DB", 
            dados_list_json=[{"item": "Dado Real 1", "valor": 100}],
            data_raspagem=test_timestamp
        ),
        ViticulturaModel(
            ano=2025, 
            aba="Teste Real DB", 
            subopcao="Outro Sub Teste Real DB", 
            dados_list_json=[{"item": "Dado Real 2", "quantidade": 200}],
            data_raspagem=test_timestamp
        )
    ]
    inserted_ids = []

    try:
        db_session_for_setup.add_all(real_db_data_to_insert)
        db_session_for_setup.commit()
        inserted_ids = [item.id for item in real_db_data_to_insert]

        with patch(PATH_RUN_FULL_SCRAPE) as mock_scrape:
            mock_scrape.return_value = []

            response = client.get("/api/viticultura/dados")

            assert response.status_code == 200
            response_data = response.json()

            expected_msg_cache_part = "Raspagem ao vivo não retornou dados"
            latest_db_timestamp_str = test_timestamp.isoformat()
            
            expected_fonte = f"Cache (Banco de Dados - Raspagem de {latest_db_timestamp_str}) (após: {expected_msg_cache_part})"
            expected_message = f"{expected_msg_cache_part}. Usando cache do BD se disponível."

            assert response_data["fonte"] == expected_fonte
            assert response_data["message"] == expected_message
            assert len(response_data["dados"]) == len(real_db_data_to_insert)

            for i, expected_item_model in enumerate(real_db_data_to_insert):
                actual_item_response = response_data["dados"][i]
                assert actual_item_response["id"] == inserted_ids[i]
                assert actual_item_response["ano"] == expected_item_model.ano
                assert actual_item_response["aba"] == expected_item_model.aba
                assert actual_item_response["subopcao"] == expected_item_model.subopcao
                assert actual_item_response["dados"] == expected_item_model.dados_list_json
                assert actual_item_response["data_raspagem"] == expected_item_model.data_raspagem.isoformat()

    finally:
        if inserted_ids:
            for item_id in inserted_ids:
                item_to_delete = db_session_for_setup.get(ViticulturaModel, item_id)
                if item_to_delete:
                    db_session_for_setup.delete(item_to_delete)
            db_session_for_setup.commit()
        db_session_for_setup.close()

        if get_current_user in app.dependency_overrides:
            del app.dependency_overrides[get_current_user]

# ------------------- NOVOS TESTES PARA /dados-especificos -------------------

def test_post_dados_especificos_success(client: TestClient):
    """
    Testa o endpoint /api/viticultura/dados-especificos para um intervalo de anos e opção.
    """
    app.dependency_overrides[get_current_user] = mock_get_current_user_override

    mock_scraped_data = [
        {"ano": 2022, "aba": "producao", "subopcao": "vinhos_de_mesa", "dados": [{"produto": "Vinho Tinto", "quantidade": 1000, "unidade_quantidade": "L"}]},
        {"ano": 2023, "aba": "producao", "subopcao": "vinhos_de_mesa", "dados": [{"produto": "Vinho Branco", "quantidade": 800, "unidade_quantidade": "L"}]}
    ]

    with patch(PATH_RUN_SCRAPE_BY_PARAMS) as mock_scrape_by_params, \
         patch(PATH_BACKGROUND_TASKS_ADD_TASK) as mock_add_task:
        mock_scrape_by_params.return_value = mock_scraped_data

        request_payload = {
            "ano_min": 2022,
            "ano_max": 2023,
            "opcao": "producao"
        }
        response = client.post(
            "/api/viticultura/dados-especificos",
            json=request_payload,
            headers={"Authorization": "Bearer fake_token"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "fonte" in data
        assert "dados" in data
        assert isinstance(data["dados"], list)
        assert data["fonte"].startswith("Embrapa")
        assert "Salvamento no banco de dados iniciado em background" in data["message"]
        assert len(data["dados"]) == 2
        for item in data["dados"]:
            assert "ano" in item
            assert "aba" in item
            assert "dados" in item
            assert "data_raspagem" in item

    del app.dependency_overrides[get_current_user]

def test_post_dados_especificos_cache(client: TestClient):
    """
    Testa o endpoint /api/viticultura/dados-especificos quando a raspagem falha e retorna dados do cache.
    """
    app.dependency_overrides[get_current_user] = mock_get_current_user_override

    with patch(PATH_RUN_SCRAPE_BY_PARAMS) as mock_scrape_by_params, \
         patch(PATH_GET_SPECIFIC_DATA_FROM_DB) as mock_get_cache:
        mock_scrape_by_params.return_value = []
        mock_get_cache.return_value = MOCK_CACHE_DATA_FROM_DB

        request_payload = {
            "ano_min": 2022,
            "ano_max": 2023,
            "opcao": "producao"
        }
        response = client.post(
            "/api/viticultura/dados-especificos",
            json=request_payload,
            headers={"Authorization": "Bearer fake_token"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "fonte" in data
        assert "dados" in data
        assert isinstance(data["dados"], list)
        assert data["fonte"].startswith("Cache")
        assert "cache do banco de dados" in data["message"] or "cache do BD" in data["message"]

    del app.dependency_overrides[get_current_user]

def test_post_dados_especificos_fail(client: TestClient):
    """
    Testa o endpoint /api/viticultura/dados-especificos quando não há dados nem na raspagem nem no cache.
    """
    app.dependency_overrides[get_current_user] = mock_get_current_user_override

    with patch(PATH_RUN_SCRAPE_BY_PARAMS) as mock_scrape_by_params, \
         patch(PATH_GET_SPECIFIC_DATA_FROM_DB) as mock_get_cache:
        mock_scrape_by_params.return_value = []
        mock_get_cache.return_value = []

        request_payload = {
            "ano_min": 2022,
            "ano_max": 2023,
            "opcao": "producao"
        }
        response = client.post(
            "/api/viticultura/dados-especificos",
            json=request_payload,
            headers={"Authorization": "Bearer fake_token"}
        )
        assert response.status_code in (500, 503)
        data = response.json()
        assert "detail" in data

    del app.dependency_overrides[get_current_user]