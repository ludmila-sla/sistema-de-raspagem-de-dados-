import os
import time
import logging
import unicodedata
import requests
from datetime import datetime

log_dir = os.path.join("logs", "logs")
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(log_dir, f"scraper_zap_{datetime.now().strftime('%Y%m%d')}.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    filemode="a"
)

API_KEY = os.environ.get("SCRAPINGANT_API_KEY")
URL_GATEWAY = "https://api.scrapingant.com/v2/general"

TIMEOUT = 120
MAX_TENTATIVAS = 3
STATUS_COM_RETRY = {409, 423, 500, 502, 503, 504}


def normalizar_slug_zap(texto):
    texto_normalizado = unicodedata.normalize("NFKD", texto).encode("ASCII", "ignore").decode("ASCII")
    return texto_normalizado.lower().replace(" ", "-")


def buscar_pagina(url_busca):
    """Chama o ScrapingAnt (com navegador) com retry e backoff. Retorna o HTML ou None."""
    headers = {"x-api-key": API_KEY}
    params = {
        "url": url_busca,
        "browser": "true",
        "proxy_type": "residential",
        "proxy_country": "BR",
    }

    for tentativa in range(1, MAX_TENTATIVAS + 1):
        try:
            response = requests.get(URL_GATEWAY, params=params, headers=headers, timeout=TIMEOUT)
        except requests.RequestException as e:
            logging.warning(f"Erro de rede no Zap (tentativa {tentativa}/{MAX_TENTATIVAS}): {e}")
        else:
            if response.status_code == 200:
                return response.text

            if response.status_code not in STATUS_COM_RETRY:
                logging.error(f"Erro HTTP {response.status_code} no Zap (sem retry):
