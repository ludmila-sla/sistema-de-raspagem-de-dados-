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
        "condominio": 0.0,
        "iptu": 0.0,
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
                        "condominio": float(condo_value),
                        "iptu": 0.0, 
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
    scripts = soup.find_all("script", type="application/ld+json")
    
    for script in scripts:
        if not script.string:
            continue
        try:
            payload = json.loads(script.string)

            if payload.get("@type") == "Product":
                offers = payload.get("offers", {})
                url_completa = offers.get("url", "")
                
                id_anuncio = None
                if url_completa:
                    id_anuncio = hashlib.md5(url_completa.strip().encode('utf-8')).hexdigest()
                
                dados_ad = {
                    "id_anuncio": id_anuncio,
                    "municipio": municipio,
                    "titulo": payload.get("name"),
                    "url": url_completa,
                    "area": float(payload.get("floorSize", {}).get("value", 0)) if payload.get("floorSize") else None,
                    "preco_total": float(offers.get("price", 0)) if offers.get("price") else None,
                    "condominio": 0.0,
                    "iptu": 0.0, 
                    "localizacao": municipio
                }
                
                if id_anuncio:
                    dados_extraidos.append(dados_ad)
                    
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

    dados_extraidos = []
    soup = BeautifulSoup(html_content, "html.parser")
    scripts = soup.find_all("script", type="application/ld+json")
    
    for script in scripts:
        if not script.string:
            continue
        try:
            payload = json.loads(script.string)

            if isinstance(payload, dict) and "mainEntity" in payload:
                listings = payload["mainEntity"]
            elif isinstance(payload, list):
                listings = payload
            else:
                listings = [payload]

            for item in listings:
                if isinstance(item, dict) and item.get("type") == "RealEstateListing":
                    url_completa = item.get("url", "").strip()
                    
                    id_anuncio = None
                    if url_completa:
                        id_anuncio = hashlib.md5(url_completa.encode('utf-8')).hexdigest()
                    
                    descricao = item.get("description", "")
                    
                    dados_ad = {
                        "id_anuncio": id_anuncio,
                        "municipio": municipio,
                        "titulo": item.get("name", "").strip(),
                        "url": url_completa,
                        "area": None,         
                        "preco_total": None,
                        "condominio": 0.0,
                        "iptu": 0.0, 
                        "localizacao": item.get("contentLocation", {}).get("name", municipio).strip()
                    }
                    
                    match_preco = re.search(r'R\$\s*-?\s*([0-9.,-]+)', descricao, re.IGNORECASE)
                    if match_preco:
                        preco_bruto = match_preco.group(1)
                        preco_corrigido = preco_bruto.lstrip('-').replace('-', ',')
                        dados_ad["preco_total"] = tratar_valor_numerico("preco_total", preco_corrigido)
                        
                    match_area = re.search(r'([0-9.,]+)\s*(?:m²|m|metros)', descricao, re.IGNORECASE)
                    if match_area:
                        dados_ad["area"] = tratar_valor_numerico("area", match_area.group(1))

                    match_condo = re.search(r'(?:condominio|condomínio)[:\s]*R\$\s*([0-9.,-]+)', descricao, re.IGNORECASE)
                    if match_condo:
                        condo_corrigido = match_condo.group(1).replace('-', ',')
                        dados_ad["condominio"] = tratar_valor_numerico("condominio", condo_corrigido)

                    match_iptu = re.search(r'(?:iptu)[:\s]*R\$\s*([0-9.,-]+)', descricao, re.IGNORECASE)
                    if match_iptu:
                        iptu_corrigido = match_iptu.group(1).replace('-', ',')
                        dados_ad["iptu"] = tratar_valor_numerico("iptu", iptu_corrigido)

                    if id_anuncio:
                        dados_extraidos.append(dados_ad)
                        
        except Exception as e:
            logging.warning(f"Erro ao fazer o parse do JSON LD do Imovelweb: {e}")
            
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

