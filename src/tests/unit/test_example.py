from unittest.mock import patch
from fastapi.testclient import TestClient # Ensure TestClient is imported if type hinting
from src.app.web.main import app
from src.app.auth.dependencies import get_current_user

# Paths to the functions that will be mocked
PATH_RUN_FULL_SCRAPE = "src.app.service.viticulture_service.run_full_scrape"
PATH_GET_LATEST_SCRAPE_GROUP = "src.app.service.viticulture_service.get_latest_scrape_group"

MOCK_USER_PAYLOAD = {"sub": "testexampleuser", "username": "testexampleuser"}

def mock_get_current_user_override():
    return MOCK_USER_PAYLOAD

def test_get_data_fails_when_scrape_and_cache_fail(client: TestClient): # Added TestClient type hint
    app.dependency_overrides[get_current_user] = mock_get_current_user_override

    with patch(PATH_RUN_FULL_SCRAPE) as mock_scrape, \
         patch(PATH_GET_LATEST_SCRAPE_GROUP) as mock_get_cache:

        mock_scrape.return_value = []
        mock_get_cache.return_value = []

        response = client.get("/api/viticultura/dados")

        assert response.status_code == 503
        response_data = response.json()

        assert "Raspagem ao vivo não retornou dados. Usando cache do BD se disponível. Cache do BD também está vazio." in response_data["detail"]

    # Clean up the dependency override
    if get_current_user in app.dependency_overrides:
        del app.dependency_overrides[get_current_user]