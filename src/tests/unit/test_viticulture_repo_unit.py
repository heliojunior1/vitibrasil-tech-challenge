import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session
from sqlalchemy import func # Importar func
from src.app.repository import viticulture_repo
from src.app.models.viticulture import Viticultura as ViticulturaModel
from src.app.domain.viticulture import ViticulturaCreate
from datetime import datetime

@pytest.fixture
def mock_db_session():
    return MagicMock(spec=Session)

def test_save_bulk_success(mock_db_session):
    current_time = datetime.utcnow()
    data_to_save = [
        ViticulturaCreate(ano=2023, aba="Aba1", subopcao="Sub1", dados=[{"d":1}], data_raspagem=current_time),
        ViticulturaCreate(ano=2024, aba="Aba2", subopcao=None, dados=[{"d":2}], data_raspagem=current_time)
    ]

    viticulture_repo.save_bulk(mock_db_session, data_to_save)

    assert mock_db_session.add_all.call_count == 1
    
    # Verificar os objetos passados para add_all
    args_add_all, _ = mock_db_session.add_all.call_args
    list_of_db_models = args_add_all[0]
    assert len(list_of_db_models) == len(data_to_save)
    for i, db_model in enumerate(list_of_db_models):
        assert isinstance(db_model, ViticulturaModel)
        assert db_model.ano == data_to_save[i].ano
        assert db_model.aba == data_to_save[i].aba
        assert db_model.subopcao == data_to_save[i].subopcao
        assert db_model.dados_list_json == data_to_save[i].dados
        assert db_model.data_raspagem == data_to_save[i].data_raspagem
        
    mock_db_session.commit.assert_called_once()
    assert mock_db_session.refresh.call_count == len(data_to_save) # refresh é chamado para cada item

def test_save_bulk_db_error(mock_db_session):
    current_time = datetime.utcnow()
    data_to_save = [
        ViticulturaCreate(ano=2023, aba="AbaError", subopcao="SubErr", dados=[{"e":1}], data_raspagem=current_time)
    ]
    mock_db_session.commit.side_effect = Exception("DB Commit Error")

    with pytest.raises(Exception, match="DB Commit Error"):
        viticulture_repo.save_bulk(mock_db_session, data_to_save)

    mock_db_session.add_all.assert_called_once()
    mock_db_session.commit.assert_called_once()
    mock_db_session.rollback.assert_called_once()
    mock_db_session.refresh.assert_not_called() # Não deve chamar refresh se o commit falhou

def test_get_latest_scrape_group_data_exists(mock_db_session):
    timestamp1 = datetime(2023, 1, 1, 10, 0, 0)
    timestamp2 = datetime(2023, 1, 1, 12, 0, 0) # Mais recente
    
    mock_data_group1 = [ViticulturaModel(id=1, data_raspagem=timestamp1)]
    mock_data_group2 = [
        ViticulturaModel(id=2, data_raspagem=timestamp2, ano=2023, aba="Recente1", dados_list_json=[{}]),
        ViticulturaModel(id=3, data_raspagem=timestamp2, ano=2023, aba="Recente2", dados_list_json=[{}])
    ]

    # Mock para func.max(ViticulturaModel.data_raspagem)
    mock_query_max = MagicMock()
    mock_db_session.query(func.max(ViticulturaModel.data_raspagem)).scalar.return_value = timestamp2
    
    # Mock para a query que busca os dados com o timestamp mais recente
    mock_query_filter = MagicMock()
    mock_db_session.query(ViticulturaModel).filter(ViticulturaModel.data_raspagem == timestamp2).all.return_value = mock_data_group2

    result = viticulture_repo.get_latest_scrape_group(mock_db_session)

    mock_db_session.query(func.max(ViticulturaModel.data_raspagem)).scalar.assert_called_once()
    mock_db_session.query(ViticulturaModel).filter(ViticulturaModel.data_raspagem == timestamp2).all.assert_called_once()
    
    assert len(result) == 2
    assert result == mock_data_group2

def test_get_latest_scrape_group_no_data(mock_db_session):
    mock_db_session.query(func.max(ViticulturaModel.data_raspagem)).scalar.return_value = None

    result = viticulture_repo.get_latest_scrape_group(mock_db_session)

    mock_db_session.query(func.max(ViticulturaModel.data_raspagem)).scalar.assert_called_once()
    mock_db_session.query(ViticulturaModel).filter().all.assert_not_called() # Não deve tentar buscar se não há timestamp
    assert result == []

def test_get_latest_scrape_group_db_error_on_max(mock_db_session):
    mock_db_session.query(func.max(ViticulturaModel.data_raspagem)).scalar.side_effect = Exception("Error fetching max timestamp")

    with pytest.raises(Exception, match="Error fetching max timestamp"):
        viticulture_repo.get_latest_scrape_group(mock_db_session)
    
    mock_db_session.query(func.max(ViticulturaModel.data_raspagem)).scalar.assert_called_once()

def test_get_latest_scrape_group_db_error_on_filter(mock_db_session):
    timestamp_latest = datetime(2023, 1, 1, 12, 0, 0)
    mock_db_session.query(func.max(ViticulturaModel.data_raspagem)).scalar.return_value = timestamp_latest
    mock_db_session.query(ViticulturaModel).filter(ViticulturaModel.data_raspagem == timestamp_latest).all.side_effect = Exception("Error fetching data")

    with pytest.raises(Exception, match="Error fetching data"):
        viticulture_repo.get_latest_scrape_group(mock_db_session)

    mock_db_session.query(func.max(ViticulturaModel.data_raspagem)).scalar.assert_called_once()
    mock_db_session.query(ViticulturaModel).filter(ViticulturaModel.data_raspagem == timestamp_latest).all.assert_called_once()