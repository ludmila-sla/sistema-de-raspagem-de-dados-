import os
import json
import logging
from bs4 import BeautifulSoup
from datetime import datetime

log_dir = os.path.join("logs", "logs")
logging.basicConfig(filename=os.path.join(log_dir, "processamento.log"), level=logging.INFO)

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
            caminho_arquivo = os.path.join(pasta_raw, arquivo)
            with open(caminho_arquivo, "r", encoding="utf-8") as f:
                html_content = f.read()
            
            soup = BeautifulSoup(html_content, "html.parser")

            
            logging.info(f"Arquivo {arquivo} parseado com sucesso.")
            
        arquivo_saida = os.path.join(pasta_processed, f"olx_dados_{data_lote}.json")
        
        with open(arquivo_saida, "w", encoding="utf-8") as f:
            json.dump(dados_processados_lote, f, indent=4, ensure_ascii=False)
            
        print(f"[+] Lote {data_lote} processado e salvo com sucesso em: {arquivo_saida}")

    except Exception as e:
        logging.exception(f"Falha crítica no processamento do lote {data_lote}. Operação abortada.")
        print(f"[-] ERRO CRÍTICO: O processamento falhou. Nada foi salvo. Verifique logs/logs/processamento.log para detalhes.")

if __name__ == "__main__":
    data_alvo = input("Digite a data do lote para processar (AAAA-MM-DD) ou pressione Enter para hoje: ")
    if not data_alvo:
        data_alvo = datetime.now().strftime("%Y-%m-%d")
    processar_lote_olx(data_alvo)
