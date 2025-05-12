import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from src.app.service.viticulture_service import obter_dados_viticultura_e_salvar, _save_data_in_background
from src.app.domain.viticulture import ViticulturaCreate, ViticulturaListResponse

# Caminhos para mock
PATH_RUN_FULL_SCRAPE_SERVICE = "src.app.service.viticulture_service.run_full_scrape"
PATH_SAVE_BULK_SERVICE = "src.app.service.viticulture_service.save_bulk"
PATH_GET_LATEST_SCRAPE_GROUP_SERVICE = "src.app.service.viticulture_service.get_latest_scrape_group"
PATH_SESSION_LOCAL_SERVICE = "src.app.service.viticulture_service.SessionLocal"


@pytest.fixture
def mock_db_session():
    return MagicMock(spec=Session)

@pytest.fixture
def mock_background_tasks():
    return MagicMock(spec=BackgroundTasks)

def test_obter_dados_viticultura_successful_scrape(mock_db_session, mock_background_tasks):
    """
    Testa o serviço quando a raspagem ao vivo é bem-sucedida.
    Verifica se os dados são transformados corretamente e se a tarefa de background é adicionada.
    """
    current_time = datetime.utcnow()
    mock_scraped_data = [
        {"ano": 2023, "aba": "Produção", "subopcao": "Vinhos de Mesa", "dados": [{"produto": "Tinto", "quantidade": 100}]},
        {"ano": 2023, "aba": "Comercialização", "subopcao": None, "dados": [{"produto": "Suco", "valor": 500}]}
    ]

    expected_viticultura_create_list = [
        ViticulturaCreate(ano=2023, aba="Produção", subopcao="Vinhos de Mesa", dados=[{"produto": "Tinto", "quantidade": 100}], data_raspagem=current_time),
        ViticulturaCreate(ano=2023, aba="Comercialização", subopcao=None, dados=[{"produto": "Suco", "valor": 500}], data_raspagem=current_time)
    ]

    with patch(PATH_RUN_FULL_SCRAPE_SERVICE, return_value=mock_scraped_data) as mock_scrape, \
         patch("src.app.service.viticulture_service.datetime") as mock_datetime:
        
        mock_datetime.utcnow.return_value = current_time

        resultado = obter_dados_viticultura_e_salvar(mock_db_session, mock_background_tasks)

        mock_scrape.assert_called_once_with(output_filepath=None)
        mock_background_tasks.add_task.assert_called_once()
        
        # Verifica o primeiro argumento da chamada a add_task (_save_data_in_background)
        # e o segundo argumento (a lista de dados que deve ser igual a expected_viticultura_create_list)
        args, _ = mock_background_tasks.add_task.call_args
        assert args[0] == _save_data_in_background
        
        # Compara os objetos ViticulturaCreate
        passed_data_to_bg_task = args[1]
        assert len(passed_data_to_bg_task) == len(expected_viticultura_create_list)
        for i, item in enumerate(passed_data_to_bg_task):
            assert item.ano == expected_viticultura_create_list[i].ano
            assert item.aba == expected_viticultura_create_list[i].aba
            assert item.subopcao == expected_viticultura_create_list[i].subopcao
            assert item.dados == expected_viticultura_create_list[i].dados
            assert item.data_raspagem == expected_viticultura_create_list[i].data_raspagem


        assert isinstance(resultado, ViticulturaListResponse)
        assert "Embrapa (Raspagem Ao Vivo - Salvamento em Andamento)" in resultado.fonte
        assert len(resultado.dados) == len(mock_scraped_data)
        assert resultado.dados[0].ano == mock_scraped_data[0]["ano"]
        assert resultado.dados[0].aba == mock_scraped_data[0]["aba"]
        assert resultado.dados[0].dados == mock_scraped_data[0]["dados"]
        assert resultado.dados[0].data_raspagem == current_time
        assert resultado.message is not None and current_time.isoformat() in resultado.message

def test_obter_dados_viticultura_scrape_fails_uses_cache(mock_db_session, mock_background_tasks):
    """
    Testa o serviço quando a raspagem falha e os dados são carregados do cache (mockado).
    """
    current_time_cache = datetime.utcnow()
    mock_cache_db_data = [
        MagicMock(id=1, ano=2022, aba="Cache Produção", subopcao="Cache Vinhos", dados_list_json=[{"p": "Cache Tinto", "q": 200}], data_raspagem=current_time_cache)
    ]

    with patch(PATH_RUN_FULL_SCRAPE_SERVICE, return_value=[]) as mock_scrape, \
         patch(PATH_GET_LATEST_SCRAPE_GROUP_SERVICE, return_value=mock_cache_db_data) as mock_get_cache:

        resultado = obter_dados_viticultura_e_salvar(mock_db_session, mock_background_tasks)

        mock_scrape.assert_called_once_with(output_filepath=None)
        mock_get_cache.assert_called_once_with(mock_db_session)
        mock_background_tasks.add_task.assert_not_called() # Não deve salvar em background se usou cache

        assert isinstance(resultado, ViticulturaListResponse)
        assert f"Cache (Banco de Dados - Raspagem de {current_time_cache.isoformat()})" in resultado.fonte
        assert "Raspagem ao vivo não retornou dados. Usando cache do BD se disponível." in resultado.message
        assert len(resultado.dados) == 1
        assert resultado.dados[0].id == mock_cache_db_data[0].id
        assert resultado.dados[0].ano == mock_cache_db_data[0].ano
        assert resultado.dados[0].dados == mock_cache_db_data[0].dados_list_json
        assert resultado.dados[0].data_raspagem == current_time_cache

def test_obter_dados_viticultura_scrape_and_cache_fail(mock_db_session, mock_background_tasks):
    """
    Testa o serviço quando tanto a raspagem quanto o cache falham.
    """
    with patch(PATH_RUN_FULL_SCRAPE_SERVICE, return_value=[]) as mock_scrape, \
         patch(PATH_GET_LATEST_SCRAPE_GROUP_SERVICE, return_value=[]) as mock_get_cache:

        resultado = obter_dados_viticultura_e_salvar(mock_db_session, mock_background_tasks)

        mock_scrape.assert_called_once_with(output_filepath=None)
        mock_get_cache.assert_called_once_with(mock_db_session)
        
        assert isinstance(resultado, ViticulturaListResponse)
        assert "Falha - Cache do BD Vazio" in resultado.fonte
        assert "Raspagem ao vivo não retornou dados. Usando cache do BD se disponível. Cache do BD também está vazio." in resultado.message
        assert len(resultado.dados) == 0

def test_save_data_in_background_success():
    """
    Testa a função _save_data_in_background em caso de sucesso.
    """
    mock_data_to_save = [
        ViticulturaCreate(ano=2023, aba="Teste BG", subopcao=None, dados=[{"d":1}], data_raspagem=datetime.utcnow())
    ]
    mock_db_instance = MagicMock(spec=Session)

    with patch(PATH_SESSION_LOCAL_SERVICE) as mock_session_local, \
         patch(PATH_SAVE_BULK_SERVICE) as mock_save_bulk_repo:
        
        mock_session_local.return_value = mock_db_instance
        
        _save_data_in_background(mock_data_to_save)

        mock_session_local.assert_called_once()
        mock_save_bulk_repo.assert_called_once_with(mock_db_instance, mock_data_to_save)
        mock_db_instance.close.assert_called_once()

def test_save_data_in_background_exception():
    """
    Testa a função _save_data_in_background quando save_bulk lança uma exceção.
    """
    mock_data_to_save = [
        ViticulturaCreate(ano=2023, aba="Teste BG Exc", subopcao=None, dados=[{"d":1}], data_raspagem=datetime.utcnow())
    ]
    mock_db_instance = MagicMock(spec=Session)

    with patch(PATH_SESSION_LOCAL_SERVICE) as mock_session_local, \
         patch(PATH_SAVE_BULK_SERVICE, side_effect=Exception("DB Error")) as mock_save_bulk_repo:
        
        mock_session_local.return_value = mock_db_instance
        
        # Não esperamos que uma exceção seja levantada para fora da função, ela deve ser capturada
        _save_data_in_background(mock_data_to_save)

        mock_session_local.assert_called_once()
        mock_save_bulk_repo.assert_called_once_with(mock_db_instance, mock_data_to_save)
        mock_db_instance.close.assert_called_once() # Garante que o close é chamado mesmo com erro