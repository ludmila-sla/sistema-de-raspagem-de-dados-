import sys
from config.cidades import APS
from config.sites import SITES
from scrapers.olx import executar_scraping_olx
from scrapers.zap import executar_scraping_zap
from scrapers.vivareal import executar_scraping_vivareal 
from scrapers.imovelweb import executar_scraping_imovelweb
from database.connection import engine
from database.models import Base

Base.metadata.create_all(engine)

sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None

def main():
    print("=========================================")
    print("[*] Iniciando Orquestrador de Scraping")
    print("=========================================")
    
    print(f"[*] Cidades carregadas pelo orquestrador: {list(APS.keys())}")
    print(f"[*] Quantidade de microrregiões prontas: {len(APS)}")
    
    if len(APS) == 0:
        print("[-] ERRO: O dicionário APS foi importado vazio. Verifique o arquivo config/cidades.py")
        return

    if SITES.get("olx"):
        print("[*] Scraper OLX: Ativo")
        executar_scraping_olx(APS)
    else:
        print("[-] Scraper OLX: Inativo")
        
    if SITES.get("zap"):
        print("[*] Scraper ZAP: Ativo")
        executar_scraping_zap(APS)
    else:
        print("[-] Scraper ZAP: Inativo")

    if SITES.get("vivareal"):
        print("[*] Scraper VivaReal: Ativo")
        executar_scraping_vivareal(APS)
    else:
        print("[-] Scraper VivaReal: Inativo")

    if SITES.get("imovelweb"):  # Bloco adicionado para o Imovelweb
        print("[*] Scraper Imovelweb: Ativo")
        executar_scraping_imovelweb(APS)
    else:
        print("[-] Scraper Imovelweb: Inativo")

if __name__ == "__main__":
    main()
