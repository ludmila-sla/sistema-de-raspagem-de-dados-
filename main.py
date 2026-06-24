from config.cidades import APS
from config.filtros import CAMPOS
from config.sites import SITES
from scrapers.olx import executar_scraping_olx

def main():
    print("=========================================")
    print("[*] Iniciando Orquestrador de Scraping")
    print("=========================================")
    
    todas_cidades = []
    for microregiao, cidades in APS.items():
        todas_cidades.extend(cidades)

    todas_cidades = list(dict.fromkeys(todas_cidades))
    
    if SITES.get("olx"):
        print("[*] Scraper OLX: Ativo")
        executar_scraping_olx(todas_cidades, CAMPOS)
    else:
        print("[-] Scraper OLX: Inativo")
        
    if SITES.get("zap"):
        pass

if __name__ == "__main__":
    main()
