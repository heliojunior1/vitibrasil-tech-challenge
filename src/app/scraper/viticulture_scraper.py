import requests
import pandas as pd
import io
from bs4 import BeautifulSoup
from datetime import datetime
from sqlalchemy.orm import Session
from urllib.parse import urlencode

from src.app.domain.viticulture import ViticulturaDTO, ViticultureCategory
from src.app.repository.viticulture_repo import RepositorioViticulture

BASE_URL = "http://vitibrasil.cnpuv.embrapa.br/index.php"

def gerar_url(opcao: str, subopcao: str, ano: int) -> str:
    params = {"opcao": opcao, "subopcao": subopcao, "ano": ano}
    return f"{BASE_URL}?{urlencode(params)}"

def baixar_csv_por_link(csv_url: str) -> pd.DataFrame:
    response = requests.get(csv_url)
    response.raise_for_status()
    return pd.read_csv(io.StringIO(response.text), sep='\t', engine='python')

def salvar_ou_retornar_do_banco(df: pd.DataFrame, categoria: ViticultureCategory, tipo: str, ano: int, url: str, db: Session):
    repo = RepositorioViticulture(db)
    registros_salvos = []

    for _, row in df.iterrows():
        try:
            dto = ViticulturaDTO(
                category=categoria,
                subcategory=tipo,
                item=row.get('Produto') or row.get('Cultivar') or row.get('Países') or "Desconhecido",
                year=ano,
                value=float(str(row.get('Quantidade') or row.get('Quantidade (Kg)') or row.get('Quantidade (L.)')).replace('.', '').replace(',', '.')),
                unit=row.get('Unidade') or 'kg',
                currency=row.get('Valor (US$)', None),
                source_url=url,
                scraped_at=datetime.utcnow()
            )
            repo.adicionar(dto)
            registros_salvos.append(dto)
        except Exception as e:
            print(f"Erro ao processar linha: {e}")

    return registros_salvos

def buscar_csv_por_categoria(categoria: ViticultureCategory, opcao: str, subopcao: str, ano: int, db: Session):
    url = gerar_url(opcao, subopcao, ano)
    print(f"Buscando dados de: {url}")
    try:
        page = requests.get(url)
        page.raise_for_status()
        soup = BeautifulSoup(page.text, "html.parser")
        links = soup.find_all("a", href=True)
        csv_links = [link['href'] for link in links if link['href'].endswith('.csv') or link['href'].endswith('.txt')]

        resultados = []
        for link in csv_links:
            full_url = link if link.startswith("http") else f"http://vitibrasil.cnpuv.embrapa.br/{link.lstrip('./')}"
            df = baixar_csv_por_link(full_url)
            dados = salvar_ou_retornar_do_banco(df, categoria, subopcao, ano, full_url, db)
            resultados.extend(dados)

        return resultados
    except Exception as e:
        print(f"Falha ao buscar CSV. Buscando no banco... Erro: {e}")
        repo = RepositorioViticulture(db)
        return repo.buscar_por_categoria_tipo_ano(categoria, subopcao, ano)
