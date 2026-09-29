# Sistema de Raspagem de Dados Imobiliários

Pipeline automatizado para coleta, processamento, normalização e armazenamento de anúncios de terrenos dos portais **OLX**, **ZAP Imóveis**, **Viva Real** e **Imovelweb**. O sistema foi desenvolvido para apoiar pesquisas territoriais a partir da construção e atualização periódica de uma base de dados imobiliários.

O projeto separa a **aquisição do HTML** do **processamento dos anúncios**. Dessa forma, lotes já coletados podem ser reprocessados sem realizar novas requisições aos portais.

## Fluxo geral

```text
Portais imobiliários
        ↓
Aquisição das páginas via ScrapingAnt
        ↓
HTML bruto (data/raw)
        ↓
Extração e processamento
        ↓
JSON processado (data/processed)
        ↓
Normalização e cálculo de campos derivados
        ↓
PostgreSQL / Supabase
        ↓
Identificação de duplicidades na base
        ↓
Google Planilhas
        ↓
Consulta e enriquecimento manual pelos pesquisadores
```

## Estrutura do projeto

```text
├── .github/
│   └── workflows/             # Automação da coleta, processamento e testes
├── config/
│   ├── cidades.py             # Municípios e arranjos populacionais pesquisados
│   ├── filtros.py             # Filtros utilizados pelos scrapers
│   └── sites.py               # Ativa/desativa cada portal
├── data/
│   ├── raw/                   # HTML bruto por site/data/município
│   └── processed/             # JSON gerado após o processamento
├── database/
│   ├── connection.py          # Conexão SQLAlchemy via DATABASE_URL
│   ├── models.py              # Modelos das tabelas locais
│   └── repository.py          # Persistência e cálculos derivados
├── logs_processamento/        # Logs do processamento
├── scrapers/
│   ├── imovelweb.py
│   ├── olx.py
│   ├── vivareal.py
│   └── zap.py
├── tests/                     # Testes dos parsers e do processamento
├── utils/
│   └── normalizador.py        # Normalização de textos e valores numéricos
├── main.py                    # Orquestra a aquisição dos HTMLs
├── processar_dados.py         # Processa os lotes e persiste os dados
└── requeriments.txt           # Dependências Python
```

## Áreas pesquisadas

Os municípios atualmente configurados em `config/cidades.py` são:

- **Bauru:** Bauru e Piratininga;
- **São José do Rio Preto:** São José do Rio Preto, Bady Bassit, Cedral, Guapiaçu e Mirassol;
- **São José dos Campos:** São José dos Campos, Caçapava e Jacarei;
- **Sorocaba:** Sorocaba, Araçoiaba da Serra, Aluminio e Votarantim.

A configuração pode ser alterada conforme o recorte territorial da pesquisa.

## 1. Aquisição das páginas

A coleta pode ser iniciada por:

```bash
python main.py
```

O `main.py` percorre os sites habilitados em `config/sites.py` e os municípios definidos em `config/cidades.py`.

Os quatro scrapers utilizam atualmente a **ScrapingAnt** como gateway para obtenção das páginas. Cada resposta HTML bem-sucedida é preservada em:

```text
data/raw/<site>/<AAAA-MM-DD>/<municipio>.html
```

A preservação do HTML bruto permite reprocessar uma coleta sem repetir a aquisição da página.

## 2. Processamento e extração

O processamento pode ser executado separadamente:

```bash
python processar_dados.py
```

O script solicita a data do lote no formato `AAAA-MM-DD`. Se nenhuma data for informada, utiliza a data atual.

As estratégias de extração variam conforme a estrutura de cada portal:

| Portal | Estratégia principal de extração |
| --- | --- |
| OLX | Parsing dos cards da página HTML com BeautifulSoup |
| ZAP Imóveis | Dados estruturados LD+JSON (`ItemList`) |
| Viva Real | Dados estruturados LD+JSON (`Product`, `ItemList`, `@graph` e `mainEntity`) |
| Imovelweb | Parsing dos cards da página HTML com BeautifulSoup |

O sistema trabalha com as páginas de resultados coletadas. Ele **não acessa individualmente cada página de imóvel para obter o texto do anúncio**. O campo `texto_anuncio` contém o texto disponível no card/listagem ou nos dados estruturados encontrados na página coletada.

Os dados processados também são gravados em:

```text
data/processed/<site>_dados_<AAAA-MM-DD>.json
```

## Campos coletados e derivados

A tabela `anuncios` utilizada no ambiente do projeto contém os seguintes campos:

| Campo | Descrição |
| --- | --- |
| `id` | Identificador interno do registro |
| `id_anuncio` | Identificador estável do anúncio |
| `data_busca` | Data da coleta/lote |
| `data_publicacao` | Data de publicação, quando disponível |
| `titulo` | Título do anúncio |
| `texto_anuncio` | Texto disponível na listagem |
| `url` | URL do anúncio |
| `endereco` | Localização/endereço extraído |
| `cidade` | Município associado ao registro |
| `cidade_busca` | Município utilizado na busca |
| `area` | Área em m² |
| `preco_total` | Preço total anunciado |
| `preco_m2` | Preço por m² calculado pelo sistema |
| `tipo_imovel` | Tipo de imóvel inferido quando possível |
| `site` | Portal de origem |
| `hash_conteudo` | Hash SHA-256 calculado a partir de atributos do anúncio |
| `duplicado_de_id` | Referência ao registro considerado original quando a base classifica o anúncio como duplicado |
| `criado_em` | Data/hora de criação do registro |

> `duplicado_de_id` existe na base PostgreSQL/Supabase utilizada pelo projeto, mas não faz parte atualmente do modelo SQLAlchemy definido em `database/models.py`. A classificação de duplicidade é realizada na camada da base de dados, e não pelo parser Python.

Os campos `titulo`, `texto_anuncio`, `url` e `data_publicacao` foram incorporados ao pipeline após as primeiras coletas. Por isso, registros históricos podem não possuir valores nesses campos.

## Identificação dos anúncios

O método de obtenção de `id_anuncio` depende da plataforma:

- **OLX:** hash MD5 da URL;
- **ZAP Imóveis:** hash MD5 da URL;
- **Viva Real:** hash MD5 da URL;
- **Imovelweb:** identificador `data-id` fornecido pelo próprio card.

Antes de inserir um registro, `database/repository.py` consulta a existência do mesmo `id_anuncio`. Caso ele já esteja armazenado, uma nova linha não é criada.

Essa regra evita reinserções do mesmo identificador, mas significa que o modelo atual **não mantém observações históricas repetidas do mesmo anúncio em diferentes meses**. Caso a pesquisa passe a exigir acompanhamento de alterações de preço ou tempo de permanência do mesmo anúncio, será necessário adotar uma tabela de histórico/observações ou permitir múltiplos registros por `id_anuncio` e data.

## Deduplicação entre registros

A prevenção de reinserção por `id_anuncio` e a classificação de duplicidades são mecanismos distintos.

O código Python impede a inserção de um identificador já existente. Já a base PostgreSQL/Supabase utilizada no projeto possui o campo `duplicado_de_id`, empregado para relacionar um registro classificado como duplicado ao registro considerado original.

O campo `hash_conteudo` é calculado no Python a partir de município, localização, área, preço total e tipo de imóvel e armazenado para rastreabilidade. A regra de classificação que preenche `duplicado_de_id` pertence à camada da base e deve ser documentada separadamente sempre que for alterada.

## Normalização e campos derivados

`utils/normalizador.py` realiza limpeza de texto e conversão de valores numéricos. Preços e áreas são convertidos para `float`.

Exemplos:

```text
R$ 130.000      -> 130000.0
R$ 189.990,00   -> 189990.0
167 m²          -> 167.0
```

Quando `area > 0` e preço e área estão disponíveis, o repository calcula:

```text
preco_m2 = preco_total / area
```

O tipo de imóvel é inferido a partir do título quando são identificados termos como `terreno`, `lote` ou `loteamento`.

## Localização

O pipeline mantém os campos `cidade`, `cidade_busca` e `endereco`.

Na implementação Python atual, `cidade` e `cidade_busca` recebem o município utilizado na execução da busca, enquanto `endereco` recebe a localização extraída do anúncio.

A qualidade e a granularidade da localização dependem do conteúdo disponibilizado por cada plataforma. Coordenadas geográficas, como latitude e longitude, não são obtidas diretamente pelo scraper.

## Data de publicação

`data_publicacao` é opcional e permanece `NULL` quando a página coletada não disponibiliza essa informação.

Na OLX, o parser também interpreta formatos relativos ou textuais, como:

```text
Hoje, 10:30
Ontem, 09:20
11 de jul, 01:49
```

O horário não é armazenado; apenas a data é persistida.

## Banco de dados

A persistência é realizada com SQLAlchemy em PostgreSQL. No ambiente do projeto, o banco é hospedado no **Supabase**.

A conexão é configurada por:

```bash
export DATABASE_URL="postgresql://usuario:senha@host:porta/banco"
```

Os campos de data permanecem com tipo `DATE` no PostgreSQL, permitindo filtros, ordenação e operações temporais sem conversão textual.

## Google Planilhas e enriquecimento manual

Além do banco estruturado, os dados são disponibilizados aos pesquisadores por meio de uma planilha no **Google Planilhas**, que consulta a base do Supabase e incorpora novos registros.

A planilha funciona como interface para consulta e complementação manual dos dados. Esse fluxo é utilizado, entre outros casos, para acrescentar informações que não são obtidas diretamente nos anúncios, como latitude e longitude necessárias às etapas posteriores de análise territorial.

O Supabase permanece como fonte estruturada dos dados coletados automaticamente; a planilha atua como camada de disponibilização e enriquecimento manual.

## Automação

O projeto utiliza GitHub Actions.

O workflow `.github/workflows/executar_scraper.yml` está configurado para:

- executar a coleta e o processamento mensalmente;
- permitir execução manual por `workflow_dispatch`;
- realizar uma consulta diária ao Supabase para mantê-lo ativo;
- persistir os JSONs processados no repositório.

O workflow `.github/workflows/testes.yml` executa os testes automaticamente em pushes e pull requests para `main` ou `master`.

## Variáveis de ambiente

Para a implementação atual dos scrapers:

```bash
export SCRAPINGANT_API_KEY="sua_chave_aqui"
export DATABASE_URL="sua_url_do_banco"
```

Para reprocessar HTMLs já armazenados, não é necessária uma nova requisição à ScrapingAnt.

## Instalação

O arquivo de dependências do projeto chama-se atualmente `requeriments.txt`:

```bash
pip install -r requeriments.txt
```

Principais dependências:

- BeautifulSoup;
- Requests;
- SQLAlchemy;
- psycopg.

## Testes

Os testes podem ser executados com:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

A suíte contém testes específicos para OLX, ZAP Imóveis, Viva Real e Imovelweb, além dos testes gerais de processamento.

Os parsers são testados a partir de HTML controlado, permitindo validar a extração sem depender de requisições reais aos portais durante os testes.

## Portais suportados

- OLX
- ZAP Imóveis
- Viva Real
- Imovelweb
