# sistema-de-raspagem-de-dados
# Pipeline de Raspagem de Dados Imobiliários

Este projeto é um pipeline automatizado de extração, tratamento e consolidação de dados imobiliários focados em microrregiões do estado de São Paulo. O sistema realiza coletas via requisições HTTP gerenciadas por proxy nos portais OLX, Zap Imóveis, VivaReal e Imovelweb, estruturando as informações brutas obtidas em arquivos consolidados prontos para análise.

##  Arquitetura e Organização do Projeto

O projeto é estruturado em camadas isoladas para garantir que falhas de rede na coleta não afetem o parser de dados, e que alterações de layout nos portais não quebrem o orquestrador.

```text
├── config/
│   ├── cidades.py           # Dicionário (APS) mapeando microrregiões e municípios alvo
│   ├── filtros.py           # Dicionário de filtros
│   └── sites.py             # Dicionário de controle (SITES) para ativar/desativar scrapers
├── data/
│   ├── raw/                 # Dados brutos salvos exatamente como vieram da web (HTML)
│   └── processed/           # Arquivos finais limpos, normalizados e convertidos para JSON
├── logs/
│   └── logs/                # Logs diários das requisições de rede (Scrapers)
├── logs_processamento/      # Logs detalhados da validação e parser dos dados
├── scrapers/                # Camada de I/O e requisições (OLX, Zap, VivaReal, Imovelweb)
│   ├── imovelweb.py         # scraper do site imovelweb
│   ├── olx.py               # scraper do site olx imoveis
│   ├── vivareal.py          # scraper do site vivareal
│   ├── zap.py               # scraper do site zap imoveis
├── utils/
│   └── normalizador.py      # Funções de limpeza de strings e conversão numérica estrita
├── tests/                   # Testes unitários para validação das Regex e hashes (CI/CD)
│   ├── test_imovelweb.py    # teste unitario do scraper imovelweb
│   ├── test_olx.py          # teste unitario do scraper olx
│   ├── test_vivareal.py     # teste unitario do scraper vivareal
│   ├── test_zap.py          # teste unitario do scraper zap imoveis
├── processar_dados.py       # Módulo centralizado de parser e higienização de lotes
├── requeriments.txt         # requisitos do sistema
└── main.py                  # Orquestrador central do pipeline de coleta
```
 Fluxo de Funcionamento
O pipeline opera em três etapas distintas executadas sequencialmente:

1. Etapa de Scraping (Orquestração de I/O)
O ponto de entrada é o arquivo main.py. Ele consome a estrutura geográfica definida em config/cidades.py e avalia quais portais estão ativos em config/sites.py.

Para cada portal ativo, o scraper correspondente é invocado.

As requisições utilizam a API do ScrapingBee com premium_proxy=true para mitigar bloqueios, Captchas e rate limiting.

O conteúdo HTML retornado é persistido de forma direta no diretório data/raw/<nome_do_site>/<data_atual>/<municipio>.html. Nenhum processamento é feito aqui.

2. Etapa de Processamento (Parser e Higienização)
Executada via processar_dados.py (ou acionada manualmente por lote de datas).

O script varre o diretório raw específico da data informada.

Mecanismos de Extração: Para portais como OLX, utiliza seletores CSS via BeautifulSoup. Para portais modernos como Imovelweb, Zap e VivaReal, o script isola e intercepta os scripts estruturados de metadados LD+JSON (Schema.org) embutidos nativamente no HTML.

Normalização: Expressões regulares específicas tratam anomalias de texto conhecidas de cada portal (como a formatação de preços R$-189.990-00 do Imovelweb). Os dados limpos passam pelo módulo utils/normalizador.py para garantir tipagem estrita (float para preços/áreas e None para ausências).

ID Único: Para evitar duplicidade e rastrear o histórico do anúncio, o link completo do imóvel é convertido em uma chave hash estável via MD5.

3. Persistência e Logs
O resultado final de cada portal é agrupado e exportado como um array de objetos JSON padronizados dentro de data/processed/<site>_dados_<data>.json.

Rastreabilidade: Logs de rede (erros de proxy, timeouts) são gravados em diretório separado dos logs de processamento (falhas de regex, JSON corrompido), simplificando a depuração em servidores de integração contínua (CI).

Como Executar
Pré-requisitos
Certifique-se de exportar sua chave de API para as variáveis de ambiente do sistema:

Bash
export SCRAPINGBEE_API_KEY="sua_chave_aqui"
Instalação de Dependências
Bash
pip install -r requirements.txt
Executar a Coleta
Bash
python main.py
Executar o Processamento de Lote Individual
Bash
python processar_dados.py
