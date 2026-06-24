import sys
from config.cidades import APS
from config.sites import SITES
from scrapers.olx import executar_scraping_olx

sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None

def main():
    print("=========================================")
    print("[*] Iniciando Orquestrador de Scraping")
    print("=========================================")
    
    if SITES.get("olx"):
        print("[*] Scraper OLX: Ativo")
        
        print(f"[*] Cidades carregadas pelo orquestrador: {list(APS.keys())}")
        print(f"[*] Quantidade de microrregiões prontas: {len(APS)}")
        
        if len(APS) == 0:
            print("[-] ERRO: O dicionário APS foi importado vazio. Verifique o arquivo config/cidades.py")
            return
            
        executar_scraping_olx(APS)
    else:
        print("[-] Scraper OLX: Inativo")
        
    if SITES.get("zap"):
        pass

if __name__ == "__main__":
    main()
