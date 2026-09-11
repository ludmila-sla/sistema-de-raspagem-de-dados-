# Sistema de Raspagem de Dados Imobiliários

Pipeline de coleta, processamento e persistência de anúncios imobiliários dos portais **OLX**, **ZAP Imóveis**, **VivaReal** e **Imovelweb**, voltado às áreas de estudo definidas no projeto.

O sistema separa a **coleta do HTML** do **processamento dos anúncios**. Isso permite reprocessar lotes já coletados sem consumir novamente créditos do ScrapingBee.

## Arquitetura

```text
├── config/
│   ├── cidades.py            # Municípios e arranjos populacionais pesquisados
│   ├── filtros.py            # Filtros utilizados pelos scrapers
│   └── sites.py              # Ativa/desativa cada portal
├── data/
│   ├── raw/                  # HTML bruto coletado por site/data/município
│   └── processed/            # JSON normalizado gerado pelo processamento
├── database/
│   ├── connection.py         # Conexão SQLAlchemy via DATABASE_URL
│   ├── models.py             # Modelos das tabelas anuncios e logs
│   └── repository.py         # Persistência e cálculos derivados
├── logs_processamento/       # Logs do parser/processamento
├── scrapers/
│   ├── imovelweb.py
│   ├── olx.py
│   ├── vivareal.py
│   └── zap.py
├── tests/
│   └── test_processamento.py # Testes locais sem acessar o ScrapingBee
├── utils/
│   └── normalizador.py       # Normalização de textos e números
├── main.py                   # Executa somente a coleta dos HTMLs
├── processar_dados.py        # Processa lotes existentes e persiste os dados
└── requeriments.txt          # Dependências Python do projeto
```

## Fluxo do sistema

### 1. Coleta

A coleta é iniciada por:

```bash
python main.py
```

O `main.py` percorre os sites habilitados em `config/sites.py` e os municípios configurados em `config/cidades.py`.

Os scrapers utilizam o ScrapingBee para obter as páginas de resultados. O HTML recebido é salvo sem tratamento em:

```text
data/raw/<site>/<AAAA-MM-DD>/<municipio>.html
```

A coleta e o processamento são independentes. Portanto, **não é necessário fazer uma nova requisição ao ScrapingBee para testar ou reprocessar um lote que já possua HTML salvo**.

### 2. Processamento

O processamento é iniciado por:

```bash
python processar_dados.py
```

O script solicita a data do lote no formato `AAAA-MM-DD` e processa os arquivos existentes em `data/raw`.

O processamento utiliza BeautifulSoup e, quando disponível, os metadados LD+JSON presentes na própria página de resultados.

**O sistema não acessa a página individual de cada imóvel para obter `texto_anuncio`.** Esse campo representa o texto disponível no card/listagem já coletado.

Para cada anúncio, o pipeline tenta obter:

| Campo | Descrição |
| --- | --- |
| `id_anuncio` | Identificador estável utilizado pelo sistema |
| `data_busca` | Data do lote/coleta |
| `data_publicacao` | Data de publicação quando disponível no portal |
| `titulo` | Título apresentado na listagem |
| `texto_anuncio` | Texto completo disponível no card/listagem |
| `url` | URL do anúncio |
| `endereco` | Localização/endereço extraído do anúncio |
| `cidade` | Cidade normalizada do anúncio |
| `cidade_busca` | Município utilizado originalmente na pesquisa |
| `area` | Área do imóvel em m² |
| `preco_total` | Preço total anunciado |
| `preco_m2` | Preço por m² calculado pelo sistema |
| `tipo_imovel` | Tipo inferido a partir do título quando possível |
| `site` | Portal de origem |
| `hash_conteudo` | Hash usado para rastreabilidade do conteúdo |
| `criado_em` | Data/hora de criação do registro no banco |

Os dados processados também são gravados em:

```text
data/processed/<site>_dados_<AAAA-MM-DD>.json
```

## Banco de dados

A conexão é feita pelo SQLAlchemy utilizando a variável de ambiente:

```bash
export DATABASE_URL="postgresql://usuario:senha@host:porta/banco"
```

No ambiente do projeto, o PostgreSQL pode ser hospedado no Supabase.

A tabela principal é `anuncios`.

Os campos `data_busca` e `data_publicacao` continuam sendo armazenados como tipos de data no PostgreSQL. Para exibição em padrão brasileiro (`DD/MM/AAAA`), recomenda-se utilizar a view de apresentação `anuncios_br` ou formatar os campos na camada de exportação/visualização.

> O formato visual de uma coluna `DATE` não é alterado por trigger. Manter o tipo `DATE` preserva filtros, ordenação e operações de data.

## Tratamento de localização

A pesquisa de um portal pode ser feita por uma região maior do que o município real do imóvel. Por isso, o projeto diferencia:

- `cidade_busca`: município usado para realizar a busca;
- `cidade`: município identificado/normalizado a partir da localização do anúncio;
- `endereco`: restante da localização do imóvel.

Quando a localização não permite determinar a cidade com segurança, o sistema mantém a informação disponível sem inventar um município.

## Data de publicação

A data de publicação é opcional. Quando o portal não disponibiliza essa informação na página de resultados, `data_publicacao` permanece `NULL`.

Na OLX também são tratados formatos como:

```text
Vila Santa Maria11 de jul, 01:49
CentroHoje, 10:30
CentroOntem, 09:20
```

O horário não é armazenado em `data_publicacao`; o projeto utiliza apenas a data.

## Normalização de valores

`utils/normalizador.py` converte preços e áreas para `float`.

Exemplos:

```text
R$ 130.000      -> 130000.0
R$ 189.990,00   -> 189990.0
167 m²          -> 167.0
```

## Variáveis de ambiente

Para executar a coleta:

```bash
export SCRAPINGBEE_API_KEY="sua_chave_aqui"
export DATABASE_URL="sua_url_do_banco"
```

Para **processar HTML já salvo e executar testes dos parsers**, não é necessário consumir créditos do ScrapingBee.

## Instalação

O arquivo de dependências do projeto atualmente se chama `requeriments.txt`:

```bash
pip install -r requeriments.txt
```

## Executando os testes sem ScrapingBee

Os testes utilizam HTML simulado e banco SQLite em memória. Nenhuma requisição aos portais ou ao ScrapingBee é executada.

```bash
python -m unittest tests/test_processamento.py -v
```

Os testes verificam, entre outros pontos:

- título e URL;
- texto completo do card;
- preço e área;
- data de publicação da OLX;
- `Hoje` e `Ontem`;
- virada de ano;
- persistência dos novos campos;
- uso da data do lote como `data_busca`.

## Observação sobre anúncios repetidos

Atualmente `id_anuncio` continua sendo único na tabela, e anúncios já existentes são ignorados pelo repository. Isso mantém o comportamento histórico do projeto.

Caso seja necessário analisar a evolução do mesmo anúncio entre diferentes datas de coleta — por exemplo, alteração de preço ou tempo de permanência — essa regra deverá ser modificada para permitir mais de uma observação do mesmo anúncio em datas diferentes.

## Portais suportados

- OLX
- ZAP Imóveis
- VivaReal
- Imovelweb
