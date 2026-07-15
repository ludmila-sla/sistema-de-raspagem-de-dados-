import os
import hashlib
import json
import logging
import re
from bs4 import BeautifulSoup
from datetime import datetime
from utils.normalizador import mapear_campo_sistema, tratar_valor_numerico
from database.repository import salvar_anuncios

log_dir = "logs_processamento"
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(log_dir, "processamento.log"), 
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

def extrair_anuncio_olx(elemento_ad, municipio):
    link_element = elemento_ad.select_one("a[class*='olx-adcard__link']")
    href = link_element.get("href") if link_element else ""
    
    id_anuncio = None
    if href:
        id_anuncio = hashlib.md5(href.strip().encode('utf-8')).hexdigest()
    
    dados_anuncio = {
        "id_anuncio": id_anuncio,
        "municipio": municipio,
        "titulo": link_element.get_text().strip() if link_element else None,
        "url": href,
        "area": None,
        "preco_total": None,
        "localizacao": None
    }
    
    preco_element = elemento_ad.select_one("[class*='olx-adcard__price']")
    if preco_element:
        dados_anuncio["preco_total"] = tratar_valor_numerico("preco_total", preco_element.get_text())
        

    localizacao_element = elemento_ad.select_one("[class*='olx-adcard__location']")
    if localizacao_element:
        texto_localizacao = localizacao_element.get_text().strip()

        texto_limpo = re.sub(r'(Hoje|Ontem|\d{1,2}\s+[A-Za-z]{3}),\s+\d{2}:\d{2}\s*$', '', texto_localizacao)
        
        dados_anuncio["localizacao"] = texto_limpo.strip().rstrip(',')
        
    detalhes = elemento_ad.select("[class*='olx-adcard__detail']") 
    for detalhe in detalhes:
        label_texto = detalhe.get("aria-label") or detalhe.get_text()
        value_texto = detalhe.get_text()

        campo_sistema = mapear_campo_sistema(label_texto)
        if campo_sistema and campo_sistema in ["area", "condominio", "iptu"]:
            dados_anuncio[campo_sistema] = tratar_valor_numerico(campo_sistema, value_texto)
                
    return dados_anuncio

def processar_lote_olx(data_lote):
    pasta_raw = os.path.join("data", "raw", "olx", data_lote)
    pasta_processed = os.path.join("data", "processed")
    
    if os.path.exists(pasta_processed) and not os.path.isdir(pasta_processed):
        os.remove(pasta_processed)
    os.makedirs(pasta_processed, exist_ok=True)
    
    if not os.path.exists(pasta_raw):
        print(f"[-] Pasta de dados brutos para a data {data_lote} não encontrada.")
        return

    arquivos_html = [f for f in os.listdir(pasta_raw) if f.endswith(".html")]
    dados_processados_lote = []

    print(f"[*] Iniciando processamento de {len(arquivos_html)} arquivos do lote {data_lote}...")

    try:
        for arquivo in arquivos_html:
            municipio_nome = arquivo.replace(".html", "").capitalize()
            caminho_arquivo = os.path.join(pasta_raw, arquivo)
            
            with open(caminho_arquivo, "r", encoding="utf-8") as f:
                html_content = f.read()
                print(f"=== DEBUG: Arquivo {arquivo} carregado com {len(html_content)} caracteres. ===")
            
            soup = BeautifulSoup(html_content, "html.parser")
            cards_anuncios = soup.select("section[class^='olx-adcard']")
            
            for card in cards_anuncios:
                try:
                    dados_ad = extrair_anuncio_olx(card, municipio_nome)
                    if dados_ad and dados_ad.get("id_anuncio"):
                        dados_processados_lote.append(dados_ad)
                except Exception as e:
                    logging.warning(f"Falha ao processar anúncio individual no arquivo {arquivo}: {e}")
            
            logging.info(f"Arquivo {arquivo} parseado com sucesso. Total parcial: {len(dados_processados_lote)}")
            
        arquivo_saida = os.path.join(pasta_processed, f"olx_dados_{data_lote}.json")
        
        with open(arquivo_saida, "w", encoding="utf-8") as f:
            json.dump(dados_processados_lote, f, indent=4, ensure_ascii=False)
            salvar_anuncios(
                dados_processados_lote,
                "olx")
            
        print(f"[+] Lote {data_lote} processado e saved em: {arquivo_saida}")

    except Exception as e:
        logging.exception(f"Falha crítica no processamento do lote {data_lote}. Operação abortada.")
        print(f"[-] ERRO CRÍTICO: O processamento falhou. Nada foi salvo. Verifique os arquivos de log.")
        
def processar_html_zap(html_content, municipio):
    dados_extraidos = []
    soup = BeautifulSoup(html_content, "html.parser")
    
    scripts = soup.find_all("script", type="application/ld+json")
    
    for script in scripts:
        if not script.string:
            continue
        try:
            payload = json.loads(script.string)

            if payload.get("@type") == "ItemList":
                itens = payload.get("itemListElement", [])
                
                for elemento in itens:
                    item = elemento.get("item", {})
                    url_completa = item.get("url", "")
                    
                    id_anuncio = None
                    if url_completa:
                        id_anuncio = hashlib.md5(url_completa.strip().encode('utf-8')).hexdigest()
                    
                    offers = item.get("offers", {})
                    condo_prop = offers.get("additionalProperty", {})
                    condo_value = condo_prop.get("value", 0.0) if condo_prop.get("name") == "Condominium Fee" else 0.0
                    
                    dados_ad = {
                        "id_anuncio": id_anuncio,
                        "municipio": municipio,
                        "titulo": item.get("name"),
                        "url": url_completa,
                        "area": float(item.get("floorSize", {}).get("value", 0)) if item.get("floorSize") else None,
                        "preco_total": float(offers.get("price", 0)) if offers.get("price") else None,
                        "localizacao": item.get("address", {}).get("addressLocality", "")
                    }
                    
                    if id_anuncio:
                        dados_extraidos.append(dados_ad)
                
                break 
                
        except Exception as e:
            logging.warning(f"Erro ao fazer o parse do JSON LD do Zap: {e}")
            
    return dados_extraidos

def processar_lote_zap(data_lote):
    pasta_raw = os.path.join("data", "raw", "zap", data_lote)
    pasta_processed = os.path.join("data", "processed")
    os.makedirs(pasta_processed, exist_ok=True)
    
    if not os.path.exists(pasta_raw):
        print(f"[-] Pasta de dados brutos Zap para a data {data_lote} não encontrada.")
        return

    arquivos_html = [f for f in os.listdir(pasta_raw) if f.endswith(".html")]
    dados_processados_lote = []

    print(f"[*] Iniciando processamento de {len(arquivos_html)} arquivos do Zap...")

    for arquivo in arquivos_html:
        municipio_nome = arquivo.replace(".html", "").capitalize()
        caminho_arquivo = os.path.join(pasta_raw, arquivo)
        
        with open(caminho_arquivo, "r", encoding="utf-8") as f:
            html_content = f.read()
            
        anuncios_arquivo = processar_html_zap(html_content, municipio_nome)
        dados_processados_lote.extend(anuncios_arquivo)
        
    arquivo_saida = os.path.join(pasta_processed, f"zap_dados_{data_lote}.json")
    with open(arquivo_saida, "w", encoding="utf-8") as f:
        json.dump(dados_processados_lote, f, indent=4, ensure_ascii=False)
        salvar_anuncios(
            dados_processados_lote,
            "zap")
        
    print(f"[+] Lote Zap {data_lote} salvo com sucesso em: {arquivo_saida}")
    
def processar_html_vivareal(html_content, municipio):

    dados_extraidos = []

    soup = BeautifulSoup(html_content, "html.parser")
    scripts = soup.select('script[type="application/ld+json"]')

    for script in scripts:

        try:

            conteudo = script.get_text(strip=True)

            if not conteudo:
                continue

            payload = json.loads(conteudo)

            produtos = []

        
            if (
                isinstance(payload, dict)
                and payload.get("@type") == "Product"
            ):
                produtos.append(payload)


            elif (
                isinstance(payload, dict)
                and payload.get("@type") == "ItemList"
            ):

                for item in payload.get("itemListElement", []):

                    if (
                        isinstance(item, dict)
                        and isinstance(item.get("item"), dict)
                    ):
                        produtos.append(item["item"])


            elif (
                isinstance(payload, dict)
                and "@graph" in payload
            ):

                for obj in payload["@graph"]:

                    if obj.get("@type") == "Product":
                        produtos.append(obj)

                    elif obj.get("@type") == "ItemList":

                        for item in obj.get("itemListElement", []):

                            if (
                                isinstance(item, dict)
                                and isinstance(item.get("item"), dict)
                            ):
                                produtos.append(item["item"])

            elif (
                isinstance(payload, dict)
                and "mainEntity" in payload
            ):

                entity = payload["mainEntity"]

                if (
                    isinstance(entity, dict)
                    and entity.get("@type") == "Product"
                ):
                    produtos.append(entity)

                elif (
                    isinstance(entity, dict)
                    and entity.get("@type") == "ItemList"
                ):

                    for item in entity.get("itemListElement", []):

                        if (
                            isinstance(item, dict)
                            and isinstance(item.get("item"), dict)
                        ):
                            produtos.append(item["item"])


            for produto in produtos:

                url_completa = produto.get("url", "").strip()

                if not url_completa:
                    continue

                id_anuncio = hashlib.md5(
                    url_completa.encode("utf-8")
                ).hexdigest()

                endereco = produto.get("address", {})

                area = None
                if produto.get("floorSize"):
                    area = tratar_valor_numerico(
                        "area",
                        produto["floorSize"].get("value")
                    )

                preco = None
                if produto.get("offers"):
                    preco = tratar_valor_numerico(
                        "preco_total",
                        produto["offers"].get("price")
                    )

                dados_extraidos.append({

                    "id_anuncio": id_anuncio,
                    "municipio": municipio,
                    "titulo": produto.get("name", "").strip(),
                    "url": url_completa,
                    "area": area,
                    "preco_total": preco,
                    "localizacao": endereco.get(
                        "addressLocality",
                        municipio
                    ).strip()

                })

        except Exception as e:
            logging.warning(f"Erro ao fazer o parse do JSON LD do VivaReal: {e}")

    return dados_extraidos


def processar_lote_vivareal(data_lote):
    pasta_raw = os.path.join("data", "raw", "vivareal", data_lote)
    pasta_processed = os.path.join("data", "processed")
    os.makedirs(pasta_processed, exist_ok=True)
    
    if not os.path.exists(pasta_raw):
        print(f"[-] Pasta de dados brutos VivaReal para a data {data_lote} não encontrada.")
        return

    arquivos_html = [f for f in os.listdir(pasta_raw) if f.endswith(".html")]
    dados_processados_lote = []

    print(f"[*] Iniciando processamento de {len(arquivos_html)} arquivos do VivaReal...")

    for arquivo in arquivos_html:
        municipio_nome = arquivo.replace(".html", "").capitalize()
        caminho_arquivo = os.path.join(pasta_raw, arquivo)
        
        with open(caminho_arquivo, "r", encoding="utf-8") as f:
            html_content = f.read()
            
        anuncios_arquivo = processar_html_vivareal(html_content, municipio_nome)
        dados_processados_lote.extend(anuncios_arquivo)
        
    arquivo_saida = os.path.join(pasta_processed, f"vivareal_dados_{data_lote}.json")
    with open(arquivo_saida, "w", encoding="utf-8") as f:
        json.dump(dados_processados_lote, f, indent=4, ensure_ascii=False)
        salvar_anuncios(
            dados_processados_lote,
            "vivareal")
        
    print(f"[+] Lote VivaReal {data_lote} salvo com sucesso em: {arquivo_saida}")
    
def processar_html_imovelweb(html_content, municipio):

    from urllib.parse import urljoin

    BASE_URL = "https://www.imovelweb.com.br"

    soup = BeautifulSoup(html_content, "html.parser")
    dados_extraidos = []

    cards = soup.select('div[data-posting-type="PROPERTY"]')

    print(f"{municipio}: encontrados {len(cards)} anúncios")

    for card in cards:

        try:

            id_anuncio = card.get("data-id")

            if not id_anuncio:
                continue

            url = ""
            link = card.select_one("a[href]")

            if link:
                url = urljoin(BASE_URL, link["href"])

            preco_total = None
            preco_tag = card.select_one('[data-qa="POSTING_CARD_PRICE"]')

            if preco_tag:
                match = re.search(r'([\d\.]+)', preco_tag.get_text())

                if match:
                    preco_total = tratar_valor_numerico(
                        "preco_total",
                        match.group(1)
                    )

            area = None
            area_tag = card.select_one('[data-qa="POSTING_CARD_FEATURES"]')

            if area_tag:
                match = re.search(r'([\d.,]+)\s*m²', area_tag.get_text())

                if match:
                    area = tratar_valor_numerico(
                        "area",
                        match.group(1)
                    )

            localizacao = municipio
            local_tag = card.select_one('[data-qa="POSTING_CARD_LOCATION"]')

            if local_tag:
                localizacao = local_tag.get_text(strip=True)

            descricao = ""
            desc_tag = card.select_one('[data-qa="POSTING_CARD_DESCRIPTION"]')

            if desc_tag:
                descricao = desc_tag.get_text(" ", strip=True)

            dados_extraidos.append({
                "id_anuncio": id_anuncio,
                "municipio": municipio,
                "titulo": descricao,
                "url": url,
                "area": area,
                "preco_total": preco_total,
                "localizacao": localizacao
            })

        except Exception as e:
            logging.exception(e)

    return dados_extraidos


def processar_lote_imovelweb(data_lote):

    pasta_raw = os.path.join("data", "raw", "imovelweb", data_lote)
    pasta_processed = os.path.join("data", "processed")
    os.makedirs(pasta_processed, exist_ok=True)
    
    if not os.path.exists(pasta_raw):
        print(f"[-] Pasta de dados brutos Imovelweb para a data {data_lote} não encontrada.")
        return

    arquivos_html = [f for f in os.listdir(pasta_raw) if f.endswith(".html")]
    dados_processados_lote = []

    print(f"[*] Iniciando processamento de {len(arquivos_html)} arquivos do Imovelweb...")

    for arquivo in arquivos_html:
        municipio_nome = arquivo.replace(".html", "").capitalize()
        caminho_arquivo = os.path.join(pasta_raw, arquivo)
        
        with open(caminho_arquivo, "r", encoding="utf-8") as f:
            html_content = f.read()
            
        anuncios_arquivo = processar_html_imovelweb(html_content, municipio_nome)
        dados_processados_lote.extend(anuncios_arquivo)
        
    arquivo_saida = os.path.join(pasta_processed, f"imovelweb_dados_{data_lote}.json")
    with open(arquivo_saida, "w", encoding="utf-8") as f:
        json.dump(dados_processados_lote, f, indent=4, ensure_ascii=False)
        salvar_anuncios(
            dados_processados_lote,
            "imovelweb")
        
    print(f"[+] Lote Imovelweb {data_lote} salvo com sucesso em: {arquivo_saida}")
    
if __name__ == "__main__":
    data_alvo = input("Digite a data do lote para processar (AAAA-MM-DD) ou pressione Enter para hoje: ")
    if not data_alvo:
        data_alvo = datetime.now().strftime("%Y-%m-%d")

    processar_lote_olx(data_alvo)
    processar_lote_zap(data_alvo)
    processar_lote_vivareal(data_alvo)
    processar_lote_imovelweb(data_alvo)

