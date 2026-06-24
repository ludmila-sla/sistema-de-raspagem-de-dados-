import os
import logging
import requests
from datetime import datetime

log_dir = os.path.join("logs", "logs")
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(log_dir, f"scraper_olx_{datetime.now().strftime('%Y%m%d')}.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    filemode="a"
)

API_KEY = os.environ.get("SCRAPINGBEE_API_KEY")
URL_GATEWAY = "https://app.scrapingbee.com/api/v1/"

_REGIOES_OLX = {
    "bauru": "regiao-de-bauru-e-marilia",
    "são josé do rio preto": "regiao-de-sao-jose-do-rio-preto",
    "são josé dos campos": "regiao-de-vale-do-paraiba-e-litoral-norte",
    "sorocaba": "regiao-de-sorocaba"
}

def normalizar_string(texto):
    import unicodedata
    texto_normalizado = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')
    return texto_normalizado.lower().replace(" ", "-")

def executar_scraping_olx(estrutura_aps):
    if not API_KEY:
        logging.error("SCRAPINGBEE_API_KEY não configurada no ambiente.")
        return

    data_atual = datetime.now().strftime("%Y-%m-%d")
    output_dir = os.path.join("data", "raw", "olx", data_atual)
    os.makedirs(output_dir, exist_ok=True)

    for microregiao, municipios in estrutura_aps.items():
        regiao_olx = _REGIOES_OLX.get(microregiao.lower(), normalizar_string(microregiao))
        
        for municipio in municipios:
            municipio_slug = normalizar_string(municipio)
            url_busca = f"https://www.olx.com.br/imoveis/terrenos/estado-sp/{regiao_olx}/{municipio_slug}"
            
            logging.info(f"Requisitando: {municipio} -> URL: {url_busca}")
            
            params = {
                "api_key": API_KEY,
                "url": url_busca,
                "country_code": "br",
                "premium_proxy": "true",
                "render_js": "false"
            }
            
            try:
                response = requests.get(URL_GATEWAY, params=params, timeout=45)
                if response.status_code == 200:
                    nome_arquivo = f"{municipio_slug}.html"
                    caminho_final = os.path.join(output_dir, nome_arquivo)
                    
                    with open(caminho_final, "w", encoding="utf-8") as f:
                        f.write(response.text)
                    logging.info(f"Sucesso ao salvar arquivo bruto: {caminho_final}")
                else:
                    logging.error(f"Erro HTTP {response.status_code} para o município {municipio}")
            except Exception as e:
                logging.exception(f"Falha crítica de rede ao processar o município {municipio}: {str(e)}")
