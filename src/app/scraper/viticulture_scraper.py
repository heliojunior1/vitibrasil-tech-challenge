from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd

def get_data_from_embrapa():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get("http://vitibrasil.cnpuv.embrapa.br/index.php?opcao=opt_02")  # Produção

    aba = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.LINK_TEXT, "Produção"))
    )
    aba.click()

    tabela = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.TAG_NAME, "table"))
    )

    linhas = tabela.find_elements(By.TAG_NAME, "tr")
    dados = []
    for linha in linhas:
        colunas = linha.find_elements(By.TAG_NAME, "td")
        dados.append([coluna.text for coluna in colunas])

    driver.quit()

    if not dados or len(dados) < 2:
        return []

    df = pd.DataFrame(dados[1:], columns=dados[0])

    # Converta para o formato esperado pela entidade Viticultura
    resultados = []
    for _, row in df.iterrows():
        resultados.append({
            "ano": int(row.get("Ano", 0)),
            "uf": row.get("Estado", "RS"),
            "categoria": "produção",
            "descricao": row.get("Produto", "Desconhecido"),
            "quantidade": float(row.get("Quantidade", 0).replace(".", "").replace(",", ".")),
            "unidade": row.get("Unidade", "litros")
        })

    return resultados