import os
import json
import logging
from bs4 import BeautifulSoup
from datetime import datetime
from utils.normalizador import mapear_campo_sistema, tratar_valor_numerico

log_dir = os.path.join("logs", "logs")
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(filename=os.path.join(log_dir, "processamento.log"), level=logging.INFO)

def extrair_anuncio_olx(elemento_ad, municipio):
    link_element = elemento_ad.select_one("a[data-testid='adcard-link']")
    href = link_element.get("href") if link_element else ""
    id_anuncio = href.split("-")[-1] if href else None
    
    dados_anuncio = {
        "id_anuncio": elemento_ad.get("data-id") or elemento_ad.get("id"),
        "municipio": municipio,
        "titulo": link_element.get_text().strip() if link_element else None,
        "url": href,
        "area": None,
        "preco_total": None,
        "condominio": 0.0,
        "iptu": 0.0,
        "localizacao": None
    }
    preco_element = elemento_ad.select_one(".olx-adcard__price")
    if preco_element:
        dados_anuncio["preco_total"] = tratar_valor_numerico("preco_total", preco_element.get_text())
        
    localizacao_element = elemento_ad.select_one(".olx-adcard__location")
    if localizacao_element:
        dados_anuncio["localizacao"] = localizacao_element.get_text().strip()
    detalhes = elemento_ad.select(".caracteristica") 
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
            
            soup = BeautifulSoup(html_content, "html.parser")

            cards_anuncios = soup.select("section.olx-adcard")
            
            for card in cards_anuncios:
                try:
                    dados_ad = extrair_anuncio_olx(card, municipio_nome)
                    if dados_ad.get("id_anuncio"):
                        dados_processados_lote.append(dados_ad)
                except Exception as e:
                    logging.warning(f"Falha ao processar anúncio individual no arquivo {arquivo}: {e}")
            
            logging.info(f"Arquivo {arquivo} parseado com sucesso. Total parcial: {len(dados_processados_lote)}")
            
        arquivo_saida = os.path.join(pasta_processed, f"olx_dados_{data_lote}.json")
        
        with open(arquivo_saida, "w", encoding="utf-8") as f:
            json.dump(dados_processados_lote, f, indent=4, ensure_ascii=False)
            
        print(f"[+] Lote {data_lote} processado e salvo com sucesso em: {arquivo_saida}")

    except Exception as e:
        logging.exception(f"Falha crítica no processamento do lote {data_lote}. Operação abortada.")
        print(f"[-] ERRO CRÍTICO: O processamento falhou. Nada foi salvo. Verifique os arquivos de log.")

if __name__ == "__main__":
    data_alvo = input("Digite a data do lote para processar (AAAA-MM-DD) ou pressione Enter para hoje: ")
    if not data_alvo:
        data_alvo = datetime.now().strftime("%Y-%m-%d")
    processar_lote_olx(data_alvo)
