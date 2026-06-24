import os
import sys
import json
import requests
from datetime import datetime
from bs4 import BeautifulSoup

API_KEY = os.environ.get("SCRAPINGBEE_API_KEY")
URL_GATEWAY = "https://app.scrapingbee.com/api/v1/"

def construir_url_olx(cidade):
    cidade_formatada = cidade.lower().replace(" ", "-")
    
    if "bauru" in cidade_formatada or "piratininga" in cidade_formatada:
        return f"https://www.olx.com.br/imoveis/terrenos/estado-sp/regiao-de-bauru-e-marilia/{cidade_formatada}"
    
    return f"https://www.olx.com.br/imoveis/terrenos/estado-sp/{cidade_formatada}"


def salvar_html_bruto(cidade, conteudo_html, data_coleta):

    diretorio_destino = os.path.join("data", "raw", data_coleta)
    os.makedirs(diretorio_destino, exist_ok=True)
    
    nome_arquivo = f"olx_{cidade.lower().replace(' ', '_')}.html"
    caminho_final = os.path.join(diretorio_destino, nome_arquivo)
    
    with open(caminho_final, "w", encoding="utf-8") as f:
        f.write(conteudo_html)
        
    print(f"[+] Backup salvo em: {caminho_final}")
    return caminho_final


def extrair_campos_filtros(caminho_html, campos_alvo):
  
    with open(caminho_html, "r", encoding="utf-8") as f:
        html_content = f.read()
        
    soup = BeautifulSoup(html_content, "html.parser")
    dados_extraidos = []
    
    script_dados = soup.find("script", id="__NEXT_DATA__")
    
    if script_dados:
        try:
            json_interno = json.loads(script_dados.string)
            print("[*] Tag __NEXT_DATA__ localizada. Pronto para extração estruturada.")
        except json.JSONDecodeError:
            print("[-] Falha ao decodificar o JSON interno do script.")
            
    return dados_extraidos


def executar_scraping_olx(lista_cidades, campos_alvo):
    if not API_KEY:
        print("[-] Erro Crítico: SCRAPINGBEE_API_KEY não foi encontrada nas variáveis de ambiente.", file=sys.stderr)
        return
        
    data_atual = datetime.now().strftime("%Y-%m-%d")
    
    for cidade in lista_cidades:
        print(f"\n[*] Iniciando coleta OLX para: {cidade}")
        url_alvo = construir_url_olx(cidade)
        
        params = {
            "api_key": API_KEY,
            "url": url_alvo,
            "country_code": "br",
            "premium_proxy": "true",
            "render_js": "false"  
        
        try:
            response = requests.get(URL_GATEWAY, params=params, timeout=30)
            
            if response.status_code == 200:
                caminho_arquivo = salvar_html_bruto(cidade, response.text, data_atual)
                
                extrair_campos_filtros(caminho_arquivo, campos_alvo)
            else:
                print(f"[-] Erro na API ScrapingBee: Status {response.status_code} para {cidade}", file=sys.stderr)
                
        except Exception as e:
            print(f"[-] Falha catastrófica ao requisitar {cidade}: {str(e)}", file=sys.stderr)
