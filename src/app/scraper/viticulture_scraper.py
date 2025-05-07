from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import re

def get_data_from_embrapa():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get("http://vitibrasil.cnpuv.embrapa.br/index.php?opcao=opt_02")

    try:
        # Pegar o ano da seção do título
        titulo = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "text_center"))
        ).text
        ano = int(re.search(r"\[(\d{4})\]", titulo).group(1))

        # Pegar a tabela com os dados
        tabela = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "tb_dados"))
        )

        linhas = tabela.find_elements(By.TAG_NAME, "tr")
        dados = []

        for linha in linhas:
            colunas = linha.find_elements(By.TAG_NAME, "td")
            if len(colunas) == 2:
                descricao = colunas[0].text.strip()
                valor_texto = colunas[1].text.strip().replace(".", "").replace(",", ".")
                try:
                    quantidade = float(valor_texto) if valor_texto != "-" else 0.0
                except ValueError:
                    quantidade = 0.0

                dados.append({
                    "ano": ano,
                    "estado": "RS",
                    "municipio": "RS",
                    "categoria": "produção",
                    "produto": descricao,
                    "quantidade": quantidade,
                    "unidade": "litros"
                })

        driver.quit()
        return dados

    except Exception as e:
        driver.quit()
        print("Erro ao raspar dados:", e)
        return []
