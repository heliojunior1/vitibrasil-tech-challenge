import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
import logging

# Importações condicionais para evitar erros
try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False
    logging.warning("Prophet não está disponível. Instale com: pip install prophet")

from src.app.domain.prediction import PredictionRequest, PredictionResponse

logger = logging.getLogger(__name__)

class PredictionService:
    
    def __init__(self):
        self.supported_options = ['producao', 'exportacao', 'importacao', 'comercializacao']
    
    def predict_production(self, db: Session, request: PredictionRequest) -> PredictionResponse:
        """
        Realiza previsão de produção/comercialização usando Prophet
        """
        try:
            if not PROPHET_AVAILABLE:
                # Retorna uma previsão mock se Prophet não estiver disponível
                return self._mock_prediction(request)
            
            # Validar opção
            if request.opcao not in self.supported_options:
                raise ValueError(f"Opção '{request.opcao}' não suportada. Opções disponíveis: {self.supported_options}")
            
            # Buscar dados históricos
            historical_data = self._get_historical_data(db, request.opcao, request.ano_minimo)
            
            if not historical_data:
                raise ValueError(f"Nenhum dado histórico encontrado para '{request.opcao}' a partir de {request.ano_minimo}")
            
            # Preparar dados para o modelo
            df_prepared = self._prepare_data_for_prediction(historical_data)
            
            if df_prepared.empty or len(df_prepared) < 2:
                raise ValueError(f"Dados insuficientes para previsão. Necessário pelo menos 2 anos de dados.")
            
            # Treinar modelo e fazer previsão
            prediction_result = self._train_and_predict(df_prepared)
            
            # Obter dados do ano anterior e próximo ano
            last_year = df_prepared['ds'].dt.year.max()
            next_year = last_year + 1
            last_year_quantity = df_prepared[df_prepared['ds'].dt.year == last_year]['y'].iloc[0]
            
            # Preparar resposta
            response = PredictionResponse(
                opcao=request.opcao,
                ano_anterior=last_year,
                quantidade_ano_anterior=round(last_year_quantity, 2),
                ano_previsto=next_year,
                quantidade_prevista=round(prediction_result['predicted_value'], 2),
                unidade=prediction_result['unit'],
                confianca=prediction_result['confidence'],
                modelo_usado="Prophet",
                dados_historicos_anos=len(df_prepared),
                data_previsao=datetime.utcnow(),
                detalhes={
                    "mae": prediction_result.get('mae'),
                    "rmse": prediction_result.get('rmse'),
                    "trend": prediction_result.get('trend'),
                    "variacao_percentual": round(((prediction_result['predicted_value'] - last_year_quantity) / last_year_quantity) * 100, 2)
                }
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Erro na previsão: {str(e)}")
            raise
    
    def _mock_prediction(self, request: PredictionRequest) -> PredictionResponse:
        """
        Retorna uma previsão mock para testes
        """
        return PredictionResponse(
            opcao=request.opcao,
            ano_anterior=2023,
            quantidade_ano_anterior=1000000.0,
            ano_previsto=2024,
            quantidade_prevista=1050000.0,
            unidade="L",
            confianca=0.75,
            modelo_usado="Mock",
            dados_historicos_anos=10,
            data_previsao=datetime.utcnow(),
            detalhes={"trend": "crescente", "note": "Previsão mock para testes"}
        )
    
    def _get_historical_data(self, db: Session, opcao: str, ano_minimo: int) -> List[Dict]:
        """
        Busca dados históricos do banco de dados
        """
        try:
            from src.app.repository.viticulture_repo import get_all_data_by_option
            all_data = get_all_data_by_option(db, opcao, ano_minimo)
            return all_data
        except Exception as e:
            logger.error(f"Erro ao buscar dados históricos: {str(e)}")
            return []
    
    def _prepare_data_for_prediction(self, historical_data: List[Dict]) -> pd.DataFrame:
        """
        Prepara dados para o modelo Prophet - soma total por ano
        """
        try:
            # Implementação simplificada
            yearly_totals = {}
            unit = "L"
            
            for record in historical_data:
                ano = record.get('ano')
                dados_json = record.get('dados_list_json', [])
                
                if not isinstance(dados_json, list) or not ano:
                    continue
                
                total_quantidade = 0
                for item in dados_json:
                    if not isinstance(item, dict):
                        continue
                    
                    quantidade = self._extract_quantity(item)
                    if quantidade and quantidade > 0:
                        total_quantidade += quantidade
                
                if ano in yearly_totals:
                    yearly_totals[ano] += total_quantidade
                else:
                    yearly_totals[ano] = total_quantidade
            
            if not yearly_totals:
                return pd.DataFrame()
            
            rows = []
            for ano, quantidade_total in yearly_totals.items():
                if quantidade_total > 0:
                    rows.append({
                        'ds': pd.to_datetime(f'{ano}-12-31'),
                        'y': quantidade_total,
                        'unidade': unit
                    })
            
            df = pd.DataFrame(rows)
            df = df.sort_values('ds').reset_index(drop=True)
            
            return df
            
        except Exception as e:
            logger.error(f"Erro na preparação dos dados: {str(e)}")
            return pd.DataFrame()
    
    def _extract_quantity(self, item: Dict) -> Optional[float]:
        """
        Extrai quantidade do item de dados
        """
        quantity_keys = ['quantidade', 'valor', 'volume', 'producao', 'total']
        
        for key in quantity_keys:
            if key in item:
                try:
                    value = item[key]
                    if isinstance(value, (int, float)):
                        return float(value)
                    elif isinstance(value, str):
                        cleaned = ''.join(c for c in value if c.isdigit() or c == '.')
                        if cleaned:
                            return float(cleaned)
                except (ValueError, TypeError):
                    continue
        
        return None
    
    def _train_and_predict(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Treina modelo Prophet e faz previsão
        """
        if not PROPHET_AVAILABLE:
            # Previsão simples baseada na média
            mean_value = df['y'].mean()
            return {
                'predicted_value': mean_value * 1.05,  # 5% de crescimento
                'confidence': 0.6,
                'unit': df['unidade'].iloc[0] if 'unidade' in df.columns else 'L',
                'trend': 'crescente'
            }
        
        try:
            model = Prophet(
                yearly_seasonality=True,
                weekly_seasonality=False,
                daily_seasonality=False,
                changepoint_prior_scale=0.05,
                interval_width=0.8
            )
            
            model.fit(df)
            future = model.make_future_dataframe(periods=1, freq='YE')
            forecast = model.predict(future)
            
            last_prediction = forecast.iloc[-1]
            predicted_value = max(0, last_prediction['yhat'])
            
            return {
                'predicted_value': predicted_value,
                'confidence': 0.75,
                'unit': df['unidade'].iloc[0] if 'unidade' in df.columns else 'L',
                'trend': 'crescente'
            }
            
        except Exception as e:
            logger.error(f"Erro no treinamento do modelo: {str(e)}")
            raise

# Instância global do serviço
prediction_service = PredictionService()