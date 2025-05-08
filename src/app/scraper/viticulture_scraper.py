import requests
import pandas as pd
import io
from bs4 import BeautifulSoup
from datetime import datetime
from sqlalchemy.orm import Session
from urllib.parse import urlencode
from src.app.domain.viticulture import ViticultureCategory
from src.app.domain.viticulture import ViticulturaDTO, ViticultureCategory
from src.app.repository.viticulture_repo import RepositorioViticulture

BASE_URL = "http://vitibrasil.cnpuv.embrapa.br/index.php"
CATEGORIAS = {cat.name: cat.value for cat in ViticultureCategory}

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
def obter_subopcoes(opcao: str) -> list[str]:
    url = f"{BASE_URL}?opcao={opcao}&ano=2023"
    response = requests.get(url)
    if response.status_code != 200:
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    botoes = soup.select("button.btn_sopt[name='subopcao']")
    return [botao["value"] for botao in botoes if "value" in botao.attrs]

def obter_intervalo_anos(opcao: str, subopcao: str = None) -> list[int]:
    url = f"{BASE_URL}?opcao={opcao}"
    if subopcao:
        url += f"&subopcao={subopcao}"
    url += "&ano=2023"

    response = requests.get(url)
    if response.status_code != 200:
        return list(range(2018, 2025))

    soup = BeautifulSoup(response.text, "html.parser")
    input_ano = soup.select_one("input[name='ano'][type='number']")

    try:
        ano_min = int(input_ano.get("min", "2018"))
        ano_max = int(input_ano.get("max", "2024"))
        return list(range(ano_min, ano_max + 1))
    except Exception:
        return list(range(2018, 2025))
