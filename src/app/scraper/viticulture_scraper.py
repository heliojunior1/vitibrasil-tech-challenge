import requests
from bs4 import BeautifulSoup
from urllib.parse import urlencode
from datetime import datetime
import time

CATEGORIA_MAP = {
    "opt_02": {"categoria": "Produção", "unidade_padrao": "Litros"},
    "opt_03": {"categoria": "Processamento", "unidade_padrao": "Kg"},
    "opt_04": {"categoria": "Comercialização", "unidade_padrao": "Litros"},
    "opt_05": {"categoria": "Importação", "unidade_padrao": "US$"},
    "opt_06": {"categoria": "Exportação", "unidade_padrao": "US$"}
}

SUBCATEGORIA_MAP = {
    "opt_03": { # Processamento
        "subopt_01": "Processamento de Uvas",
        "subopt_02": "Viníferas",
        "subopt_03": "Americanas e Híbridas",
        "subopt_04": "Uvas de Mesa",
        "subopt_05": "Sem Classificação"
    },
    "opt_05": { # Importação
        "subopt_01": "Vinhos de Mesa",
        "subopt_02": "Espumantes",
        "subopt_03": "Uvas Frescas",
        "subopt_04": "Uvas Passas",
        "subopt_05": "Suco de Uva"
    },
    "opt_06": { # Exportação
        "subopt_01": "Vinhos de Mesa",
        "subopt_02": "Espumantes",
        "subopt_03": "Uvas Frescas",
        "subopt_04": "Suco de Uva"
    }
}

def get_data_from_embrapa(year: int, option: str, suboption: str = None):
    base_url = "http://vitibrasil.cnpuv.embrapa.br/index.php?"
    params = {'ano': year, 'opcao': option}
    if suboption:
        params['subopcao'] = suboption
    url = base_url + urlencode(params)

    # Requisições com retry
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            print(f"Carregando {url} (Tentativa {attempt}/{max_retries})")
            resp = requests.get(url, timeout=(30, 60))
            resp.raise_for_status()
            break
        except requests.exceptions.RequestException as e:
            print(f"Erro ao carregar: {e}")
            if attempt == max_retries:
                return []
            time.sleep(2 * attempt)
    else:
        return []

    soup = BeautifulSoup(resp.content, 'lxml')

    # Título (para ajustar unidade se necessário)
    titulo_div = soup.find("div", class_="text_center")
    titulo_text = titulo_div.find("h3").get_text(strip=True) if titulo_div and titulo_div.find("h3") else ""

    # Determina categoria e unidade padrão
    cat_info = CATEGORIA_MAP.get(option, {"categoria": "Desconhecida", "unidade_padrao": "N/A"})
    categoria = cat_info["categoria"]
    unidade_padrao = cat_info["unidade_padrao"]

    # 1) Seletor específico para tabela de dados
    tabela_bs = soup.select_one("table.tb_dados")
    if not tabela_bs:
        # fallback: qualquer tabela com classe tb_dados
        tabela_bs = soup.find(lambda tag: tag.name == "table" and "tb_dados" in (tag.get('class') or []))
    if not tabela_bs:
        print(f"Tabela de dados não encontrada em {url}")
        # Salva HTML para debug
        debug_file = f"debug_NO_TABLE_{option}_{year}_{suboption or 'none'}.html"
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write(soup.prettify())
        print(f"HTML salvo em: {debug_file}")
        return []

    # 2) Extrai cabeçalho
    header_row = tabela_bs.select_one("thead tr")
    if header_row:
        header_cells = header_row.find_all(['th', 'td'])
        start_index = 1
    else:
        all_rows = tabela_bs.find_all('tr')
        if not all_rows:
            return []
        header_cells = all_rows[0].find_all(['th', 'td'])
        start_index = 1

    # Define índices de colunas
    produto_col = 0
    valor_col = 1
    for idx, cell in enumerate(header_cells):
        text = cell.get_text(strip=True).lower()
        if any(kw in text for kw in ["produto", "cultivar", "descriç", "item"]):
            produto_col = idx
        if any(kw in text for kw in ["quantidade", "valor", str(year)]):
            valor_col = idx

    # Ajustes para Importação/Exportação (US$)
    if unidade_padrao == "US$":
        for idx, cell in enumerate(header_cells[::-1]):
            ctext = cell.get_text(strip=True).lower()
            if "valor" in ctext or "us$" in ctext:
                valor_col = len(header_cells) - 1 - idx
                break

    # 3) Itera só no <tbody>
    body = tabela_bs.find('tbody')
    rows = body.find_all('tr') if body else tabela_bs.find_all('tr')[start_index:]

    dados = []
    for row in rows:
        cols = row.find_all('td')
        if not cols:
            continue
        desc = cols[produto_col].get_text(strip=True)
        val_text = cols[valor_col].get_text(strip=True)
        if not desc or desc.lower().startswith("total"):
            continue

        # Limpa e converte valor
        val_clean = val_text.replace('.', '').replace(',', '.')
        try:
            val = float(val_clean) if val_clean and val_clean != '-' else 0.0
        except ValueError:
            val = 0.0

        unit = unidade_padrao
        currency = "USD" if unidade_padrao == "US$" else None

        # Refina segundo o título
        if "us$" in titulo_text.lower():
            unit = "US$"
            currency = "USD"

        sub_name = None
        if suboption and option in SUBCATEGORIA_MAP:
            sub_name = SUBCATEGORIA_MAP[option].get(suboption)

        dados.append({
            "category": categoria,
            "subcategory_name": sub_name,
            "item_name": desc,
            "year": year,
            "value": val,
            "measurement_unit": unit,
            "currency_code": currency,
            "source_url": url,
            "scraped_at": datetime.now().isoformat()
        })

    if not dados:
        print(f"Nenhum dado coletado para ano={year}, opcao={option}, subopcao={suboption}")
    return dados


if __name__ == '__main__':
    ANO_INICIAL = 2022
    ANO_FINAL = 2022
    OPCOES_PARA_RASPAR = {
        "opt_02": {"nome": "Produção", "subopcoes": None},
        "opt_03": {"nome": "Processamento", "subopcoes": ["subopt_01", "subopt_02", "subopt_03", "subopt_04", "subopt_05"]},
        "opt_04": {"nome": "Comercialização", "subopcoes": None},
        "opt_05": {"nome": "Importação", "subopcoes": ["subopt_01", "subopt_02", "subopt_03", "subopt_04", "subopt_05"]},
        "opt_06": {"nome": "Exportação", "subopcoes": ["subopt_01", "subopt_02", "subopt_03", "subopt_04"]}
    }

    all_data = []
    for ano in range(ANO_INICIAL, ANO_FINAL + 1):
        for opt_code, info in OPCOES_PARA_RASPAR.items():
            subopts = info["subopcoes"]
            if subopts:
                for sub in subopts:
                    print(f"\n--- {info['nome']} - {sub} | Ano: {ano} ---")
                    time.sleep(2)
                    resultados = get_data_from_embrapa(ano, opt_code, sub)
                    all_data.extend(resultados)
            else:
                print(f"\n--- {info['nome']} | Ano: {ano} ---")
                time.sleep(2)
                resultados = get_data_from_embrapa(ano, opt_code)
                all_data.extend(resultados)

    print(f"Total registros: {len(all_data)}")
    if all_data:
        import json
        file_out = f"dados_embrapa_{ANO_INICIAL}_{ANO_FINAL}.json"
        with open(file_out, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        print(f"Dados salvos em: {file_out}")
