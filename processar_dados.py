import hashlib
import json
import logging
import os
import re
from datetime import date, datetime, timedelta
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from database.repository import salvar_anuncios
from utils.normalizador import mapear_campo_sistema, tratar_valor_numerico

log_dir = "logs_processamento"
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(log_dir, "processamento.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

MESES_PT = {
    "jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
    "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12
}


def normalizar_texto_card(elemento):
    return re.sub(r"\s+", " ", elemento.get_text(" ", strip=True)).strip()


def converter_data_busca(valor):
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if not valor:
        return datetime.now().date()

    for formato in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(str(valor), formato).date()
        except ValueError:
            continue

    return datetime.now().date()


def extrair_data_publicacao_olx(texto, data_busca=None):
    if not texto:
        return None, texto

    referencia = converter_data_busca(data_busca)
    texto_limpo = texto.strip()

    if re.search(r"Hoje,?\s*\d{1,2}:\d{2}\s*$", texto_limpo, re.I):
        localizacao = re.sub(r"Hoje,?\s*\d{1,2}:\d{2}\s*$", "", texto_limpo, flags=re.I).strip().rstrip(",")
        return referencia, localizacao

    if re.search(r"Ontem,?\s*\d{1,2}:\d{2}\s*$", texto_limpo, re.I):
        localizacao = re.sub(r"Ontem,?\s*\d{1,2}:\d{2}\s*$", "", texto_limpo, flags=re.I).strip().rstrip(",")
        return referencia - timedelta(days=1), localizacao

    match = re.search(
        r"(\d{1,2})\s+de\s+(jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)[a-zçãéíóúâêô]*,\s*\d{1,2}:\d{2}\s*$",
        texto_limpo,
        re.I
    )
    if not match:
        return None, texto_limpo

    dia = int(match.group(1))
    mes = MESES_PT[match.group(2).lower()[:3]]
    ano = referencia.year

    try:
        data_publicacao = date(ano, mes, dia)
        if data_publicacao > referencia:
            data_publicacao = date(ano - 1, mes, dia)
    except ValueError:
        data_publicacao = None

    localizacao = texto_limpo[:match.start()].strip().rstrip(",")
    return data_publicacao, localizacao


def extrair_data_iso(valor):
    if not valor:
        return None

    valor = str(valor).strip()
    formatos = ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%m/%d/%y", "%d/%m/%Y")

    for formato in formatos:
        try:
            texto = valor[:19] if formato == "%Y-%m-%dT%H:%M:%S" else valor
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue

    return None


def extrair_anuncio_olx(elemento_ad, municipio, data_busca=None):
    link_element = elemento_ad.select_one("a[class*='olx-adcard__link']")
    href = link_element.get("href") if link_element else ""
    id_anuncio = hashlib.md5(href.strip().encode("utf-8")).hexdigest() if href else None

    dados_anuncio = {
        "id_anuncio": id_anuncio,
        "municipio": municipio,
        "titulo": link_element.get_text(" ", strip=True) if link_element else None,
        "texto_anuncio": normalizar_texto_card(elemento_ad),
        "url": href,
        "data_publicacao": None,
        "area": None,
        "preco_total": None,
        "localizacao": None
    }

    preco_element = elemento_ad.select_one("[class*='olx-adcard__price']")
    if preco_element:
        dados_anuncio["preco_total"] = tratar_valor_numerico("preco_total", preco_element.get_text())

    localizacao_element = elemento_ad.select_one("[class*='olx-adcard__location']")
    if localizacao_element:
        data_publicacao, localizacao = extrair_data_publicacao_olx(
            localizacao_element.get_text(" ", strip=True),
            data_busca
        )
        dados_anuncio["data_publicacao"] = data_publicacao
        dados_anuncio["localizacao"] = localizacao

    for detalhe in elemento_ad.select("[class*='olx-adcard__detail']"):
        label_texto = detalhe.get("aria-label") or detalhe.get_text()
        campo_sistema = mapear_campo_sistema(label_texto)
        if campo_sistema == "area":
            dados_anuncio["area"] = tratar_valor_numerico("area", detalhe.get_text())

    return dados_anuncio


def processar_html_olx(html_content, municipio, data_busca=None):
    soup = BeautifulSoup(html_content, "html.parser")
    dados = []

    for card in soup.select("section[class^='olx-adcard']"):
        if not card.select_one("a[class*='olx-adcard__link']"):
            continue
        dados.append(extrair_anuncio_olx(card, municipio, data_busca))

    return dados


def processar_lote_olx(data_lote):
    pasta_raw = os.path.join("data", "raw", "olx", data_lote)
    pasta_processed = os.path.join("data", "processed")
    os.makedirs(pasta_processed, exist_ok=True)

    if not os.path.exists(pasta_raw):
        print(f"[-] Pasta de dados brutos para a data {data_lote} não encontrada.")
        return

    arquivos_html = [f for f in os.listdir(pasta_raw) if f.endswith(".html")]
    dados_processados_lote = []
    print(f"[*] Iniciando processamento de {len(arquivos_html)} arquivos do lote {data_lote}...")

    for arquivo in arquivos_html:
        try:
            municipio_nome = arquivo.replace(".html", "").capitalize()
            caminho_arquivo = os.path.join(pasta_raw, arquivo)

            with open(caminho_arquivo, "r", encoding="utf-8") as f:
                html_content = f.read()

            dados_processados_lote.extend(processar_html_olx(html_content, municipio_nome, data_lote))
            logging.info(f"Arquivo {arquivo} parseado com sucesso. Total parcial: {len(dados_processados_lote)}")
        except Exception as e:
            logging.exception(f"Falha ao processar arquivo OLX {arquivo}: {e}")

    arquivo_saida = os.path.join(pasta_processed, f"olx_dados_{data_lote}.json")
    with open(arquivo_saida, "w", encoding="utf-8") as f:
        json.dump(dados_processados_lote, f, indent=4, ensure_ascii=False, default=str)

    salvar_anuncios(dados_processados_lote, "olx", data_lote)
    print(f"[+] Lote OLX {data_lote} salvo com sucesso em: {arquivo_saida}")


def processar_html_zap(html_content, municipio):
    dados_extraidos = []
    soup = BeautifulSoup(html_content, "html.parser")

    for script in soup.find_all("script", type="application/ld+json"):
        if not script.string:
            continue

        try:
            payload = json.loads(script.string)
        except Exception as e:
            logging.warning(f"Erro ao fazer o parse do JSON LD do Zap: {e}")
            continue

        if not isinstance(payload, dict) or payload.get("@type") != "ItemList":
            continue

        for elemento in payload.get("itemListElement", []):
            item = elemento.get("item", {})
            url_completa = item.get("url", "")
            if not url_completa:
                continue

            offers = item.get("offers", {}) if isinstance(item.get("offers", {}), dict) else {}
            descricao = item.get("description") or item.get("name")

            dados_extraidos.append({
                "id_anuncio": hashlib.md5(url_completa.strip().encode("utf-8")).hexdigest(),
                "municipio": municipio,
                "titulo": item.get("name"),
                "texto_anuncio": descricao,
                "url": url_completa,
                "data_publicacao": extrair_data_iso(item.get("datePosted")),
                "area": tratar_valor_numerico("area", item.get("floorSize", {}).get("value")) if isinstance(item.get("floorSize"), dict) else None,
                "preco_total": tratar_valor_numerico("preco_total", offers.get("price")),
                "localizacao": item.get("address", {}).get("addressLocality", "") if isinstance(item.get("address", {}), dict) else ""
            })

        break

    return dados_extraidos


def processar_lote_zap(data_lote):
    _processar_lote_generico("zap", data_lote, processar_html_zap)


def _coletar_produtos_jsonld(payload):
    produtos = []

    if isinstance(payload, dict) and payload.get("@type") == "Product":
        produtos.append(payload)
    elif isinstance(payload, dict) and payload.get("@type") == "ItemList":
        produtos.extend(
            item.get("item")
            for item in payload.get("itemListElement", [])
            if isinstance(item, dict) and isinstance(item.get("item"), dict)
        )
    elif isinstance(payload, dict) and "@graph" in payload:
        for obj in payload["@graph"]:
            produtos.extend(_coletar_produtos_jsonld(obj))
    elif isinstance(payload, dict) and "mainEntity" in payload:
        entity = payload["mainEntity"]
        if isinstance(entity, list):
            for obj in entity:
                produtos.extend(_coletar_produtos_jsonld(obj))
        else:
            produtos.extend(_coletar_produtos_jsonld(entity))

    return [produto for produto in produtos if produto]


def processar_html_vivareal(html_content, municipio):
    dados_extraidos = []
    soup = BeautifulSoup(html_content, "html.parser")

    for script in soup.select('script[type="application/ld+json"]'):
        try:
            payload = json.loads(script.get_text(strip=True))
        except Exception as e:
            logging.warning(f"Erro ao fazer o parse do JSON LD do VivaReal: {e}")
            continue

        for produto in _coletar_produtos_jsonld(payload):
            url_completa = str(produto.get("url", "")).strip()
            if not url_completa:
                continue

            endereco = produto.get("address", {}) if isinstance(produto.get("address", {}), dict) else {}
            offers = produto.get("offers", {}) if isinstance(produto.get("offers", {}), dict) else {}
            descricao = produto.get("description") or produto.get("name")

            dados_extraidos.append({
                "id_anuncio": hashlib.md5(url_completa.encode("utf-8")).hexdigest(),
                "municipio": municipio,
                "titulo": str(produto.get("name", "")).strip(),
                "texto_anuncio": descricao,
                "url": url_completa,
                "data_publicacao": extrair_data_iso(produto.get("datePosted")),
                "area": tratar_valor_numerico("area", produto.get("floorSize", {}).get("value")) if isinstance(produto.get("floorSize"), dict) else None,
                "preco_total": tratar_valor_numerico("preco_total", offers.get("price")),
                "localizacao": str(endereco.get("addressLocality", municipio)).strip()
            })

    return dados_extraidos


def processar_lote_vivareal(data_lote):
    _processar_lote_generico("vivareal", data_lote, processar_html_vivareal)


def processar_html_imovelweb(html_content, municipio):
    base_url = "https://www.imovelweb.com.br"
    soup = BeautifulSoup(html_content, "html.parser")
    dados_extraidos = []

    for card in soup.select('div[data-posting-type="PROPERTY"]'):
        try:
            id_anuncio = card.get("data-id")
            if not id_anuncio:
                continue

            link = card.select_one("a[href]")
            url = urljoin(base_url, link["href"]) if link else ""

            preco_tag = card.select_one('[data-qa="POSTING_CARD_PRICE"]')
            preco_total = tratar_valor_numerico("preco_total", preco_tag.get_text()) if preco_tag else None

            area_tag = card.select_one('[data-qa="POSTING_CARD_FEATURES"]')
            area_match = re.search(r"([\d.,]+)\s*m²", area_tag.get_text()) if area_tag else None
            area = tratar_valor_numerico("area", area_match.group(1)) if area_match else None

            local_tag = card.select_one('[data-qa="POSTING_CARD_LOCATION"]')
            localizacao = local_tag.get_text(" ", strip=True) if local_tag else municipio

            titulo_tag = card.select_one('[data-qa="POSTING_CARD_TITLE"]')
            desc_tag = card.select_one('[data-qa="POSTING_CARD_DESCRIPTION"]')
            titulo = titulo_tag.get_text(" ", strip=True) if titulo_tag else (desc_tag.get_text(" ", strip=True) if desc_tag else None)

            time_tag = card.select_one("time[datetime]")
            data_publicacao = extrair_data_iso(time_tag.get("datetime")) if time_tag else None

            dados_extraidos.append({
                "id_anuncio": id_anuncio,
                "municipio": municipio,
                "titulo": titulo,
                "texto_anuncio": normalizar_texto_card(card),
                "url": url,
                "data_publicacao": data_publicacao,
                "area": area,
                "preco_total": preco_total,
                "localizacao": localizacao
            })
        except Exception as e:
            logging.exception(f"Erro ao processar anúncio do Imovelweb: {e}")

    return dados_extraidos


def processar_lote_imovelweb(data_lote):
    _processar_lote_generico("imovelweb", data_lote, processar_html_imovelweb)


def _processar_lote_generico(site, data_lote, parser):
    pasta_raw = os.path.join("data", "raw", site, data_lote)
    pasta_processed = os.path.join("data", "processed")
    os.makedirs(pasta_processed, exist_ok=True)

    if not os.path.exists(pasta_raw):
        print(f"[-] Pasta de dados brutos {site} para a data {data_lote} não encontrada.")
        return

    arquivos_html = [f for f in os.listdir(pasta_raw) if f.endswith(".html")]
    dados_processados_lote = []
    print(f"[*] Iniciando processamento de {len(arquivos_html)} arquivos do {site}...")

    for arquivo in arquivos_html:
        try:
            municipio_nome = arquivo.replace(".html", "").capitalize()
            caminho_arquivo = os.path.join(pasta_raw, arquivo)

            with open(caminho_arquivo, "r", encoding="utf-8") as f:
                html_content = f.read()

            dados_processados_lote.extend(parser(html_content, municipio_nome))
        except Exception as e:
            logging.exception(f"Falha ao processar arquivo {site} {arquivo}: {e}")

    arquivo_saida = os.path.join(pasta_processed, f"{site}_dados_{data_lote}.json")
    with open(arquivo_saida, "w", encoding="utf-8") as f:
        json.dump(dados_processados_lote, f, indent=4, ensure_ascii=False, default=str)

    salvar_anuncios(dados_processados_lote, site, data_lote)
    print(f"[+] Lote {site} {data_lote} salvo com sucesso em: {arquivo_saida}")


if __name__ == "__main__":
    data_alvo = input("Digite a data do lote para processar (AAAA-MM-DD) ou pressione Enter para hoje: ")
    if not data_alvo:
        data_alvo = datetime.now().strftime("%Y-%m-%d")

    processar_lote_olx(data_alvo)
    processar_lote_zap(data_alvo)
    processar_lote_vivareal(data_alvo)
    processar_lote_imovelweb(data_alvo)