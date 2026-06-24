from config.cidades import APS
from config.sites import SITES
from scrapers.olx import executar_scraping_olx

def main():
    print("=========================================")
    print("[*] Iniciando Orquestrador de Scraping")
    print("=========================================")
    
    if SITES.get("olx"):
        print("[*] Scraper OLX: Ativo")
        executar_scraping_olx(APS)
    else:
        print("[-] Scraper OLX: Inativo")
        
    if SITES.get("zap"):
        pass

if __name__ == "__main__":
    main()
