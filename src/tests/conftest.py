from fastapi.testclient import TestClient
from src.app.web.main import app # Changed from 'your_application'

import pytest

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c