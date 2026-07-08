import os
import logging
import requests
import unicodedata
from datetime import datetime

log_dir = os.path.join("logs", "logs")
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(log_dir, f"scraper_vivareal_{datetime.now().strftime('%Y%m%d')}.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    filemode="a"
)

API_KEY = os.environ.get("SCRAPINGBEE_API_KEY")
URL_GATEWAY = "https://app.scrapingbee.com/api/v1/"

def normalizar_string(texto):
    texto_normalizado = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')
    return texto_normalizado.lower().replace(" ", "-")

def gerar_url_vivareal(municipio_slug):
    """Gera a URL do VivaReal focada exclusivamente em venda de Lotes e Terrenos."""
    return f"https://www.vivareal.com.br/venda/sp/{municipio_slug}/lote-terreno_secao/"

def executar_scraping_vivareal(estrutura_aps):
    if not API_KEY:
        logging.error("SCRAPINGBEE_API_KEY não configurada no ambiente para o VivaReal.")
        return

    data_atual = datetime.now().strftime("%Y-%m-%d")
    output_dir = os.path.join("data", "raw", "vivareal", data_atual)
    os.makedirs(output_dir, exist_ok=True)

    print("\n=========================================")
    print("[*] Iniciando Coleta VivaReal (Terrenos)")
    print("=========================================")

    for microregiao, municipios in estrutura_aps.items():
        print(f"[*] Processando microrregião VivaReal: {microregiao}")
        
        for municipio in municipios:
            municipio_slug = normalizar_string(municipio)
            url_busca = gerar_url_vivareal(municipio_slug)
            
            print(f"    [->] Coletando {municipio} via ScrapingBee...")
            logging.info(f"Requisitando VivaReal: {municipio} -> URL: {url_busca}")
            
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
                    print(f"    [+] Sucesso ao salvar arquivo bruto: {municipio_slug}.html")
                    logging.info(f"Sucesso ao salvar arquivo bruto VivaReal: {caminho_final}")
                else:
                    print(f"    [-] Erro HTTP {response.status_code} para {municipio}")
                    logging.error(f"Erro HTTP {response.status_code} no VivaReal para o município {municipio}")
            except Exception as e:
                print(f"    [-] Falha crítica de rede em {municipio}")
                logging.exception(f"Falha crítica de rede ao processar VivaReal para o município {municipio}: {str(e)}")
