import argparse
import json
import os
import re
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.connection import engine
from database.models import Anuncio
from database.repository import converter_data
from utils.normalizador import tratar_valor_numerico


PASTA_PROCESSED = Path("data/processed")
PADRAO_ARQUIVO = re.compile(r"^(?P<site>[a-z0-9_-]+)_dados_(?P<data>\d{4}-\d{2}-\d{2})\.json$", re.I)
PADRAO_PRECO_TEXTO = re.compile(r"R\$\s*([\d.]+(?:,\d{1,2})?)", re.I)

TOLERANCIA_PRECO = 0.05
TAMANHO_LOTE = 50


def texto_valido(valor):
    if valor is None:
        return None

    texto = str(valor).strip()
    return texto or None


def extrair_preco_titulo(titulo):
    titulo = texto_valido(titulo)
    if not titulo:
        return None

    match = PADRAO_PRECO_TEXTO.search(titulo)
    if not match:
        return None

    preco = tratar_valor_numerico("preco_total", match.group(1))
    if preco is not None and preco > 0:
        return preco

    return None


def aproximadamente_mil_vezes(preco_atual, preco_texto):
    if preco_atual is None or preco_atual <= 0:
        return False

    esperado = preco_atual * 1000

    if esperado <= 0:
        return False

    diferenca_relativa = abs(preco_texto - esperado) / esperado
    return diferenca_relativa <= TOLERANCIA_PRECO


def preco_recuperavel(registro, anuncio, site):
    if site.lower() != "olx":
        return None

    preco_texto = extrair_preco_titulo(anuncio.get("titulo"))
    if preco_texto is None or preco_texto < 10000:
        return None

    preco_atual = registro.preco_total

    if preco_atual is None:
        return preco_texto

    if preco_atual < 10000 and aproximadamente_mil_vezes(preco_atual, preco_texto):
        return preco_texto

    return None


def carregar_arquivos():
    if not PASTA_PROCESSED.exists():
        raise FileNotFoundError(f"Pasta não encontrada: {PASTA_PROCESSED}")

    arquivos = []

    for caminho in sorted(PASTA_PROCESSED.glob("*_dados_*.json")):
        match = PADRAO_ARQUIVO.match(caminho.name)
        if match:
            arquivos.append((caminho, match.group("site"), match.group("data")))

    return arquivos


def carregar_json(caminho):
    with caminho.open("r", encoding="utf-8") as arquivo:
        dados = json.load(arquivo)

    if not isinstance(dados, list):
        raise ValueError(f"{caminho} não contém uma lista de anúncios.")

    return dados


def preencher_se_vazio(registro, atributo, valor):
    valor = texto_valido(valor)

    if valor is None:
        return False

    atual = getattr(registro, atributo)

    if atual is None or (isinstance(atual, str) and not atual.strip()):
        setattr(registro, atributo, valor)
        return True

    return False


def preencher_data_se_vazia(registro, atributo, valor):
    if getattr(registro, atributo) is not None:
        return False

    data = converter_data(valor)
    if data is None:
        return False

    setattr(registro, atributo, data)
    return True


def salvar_lote(session, aplicar, pendentes):
    if pendentes == 0:
        return 0

    if aplicar:
        session.commit()
        print(f"[LOTE] {pendentes} registro(s) gravado(s).")
    else:
        # No dry-run não fazemos flush nem commit.
        # As alterações ficam apenas na sessão e serão descartadas no final.
        pass

    return 0


def processar(aplicar=False):
    resumo = {
        "arquivos": 0,
        "itens_json": 0,
        "registros_encontrados_banco": 0,
        "registros_nao_encontrados": 0,
        "registros_alterados": 0,
        "precos_recuperados": 0,
        "titulos_preenchidos": 0,
        "urls_preenchidas": 0,
        "datas_publicacao_preenchidas": 0,
        "cidades_busca_preenchidas": 0,
        "textos_preenchidos": 0,
        "enderecos_preenchidos": 0,
        "lotes_gravados": 0
    }

    ids_encontrados = set()
    ids_nao_encontrados = set()
    ids_alterados = set()

    pendentes = 0

    with Session(engine, autoflush=False) as session:
        for caminho, site, data_lote in carregar_arquivos():
            resumo["arquivos"] += 1

            try:
                anuncios = carregar_json(caminho)
            except Exception as erro:
                print(f"[ERRO] {caminho}: {erro}")
                continue

            for anuncio in anuncios:
                resumo["itens_json"] += 1

                id_anuncio = texto_valido(anuncio.get("id_anuncio"))
                if not id_anuncio:
                    continue

                with session.no_autoflush:
                    registro = session.scalar(
                        select(Anuncio).where(Anuncio.id_anuncio == id_anuncio)
                    )

                if registro is None:
                    ids_nao_encontrados.add(id_anuncio)
                    continue

                ids_encontrados.add(id_anuncio)
                alterado = False

                if preencher_se_vazio(registro, "titulo", anuncio.get("titulo")):
                    resumo["titulos_preenchidos"] += 1
                    alterado = True

                if preencher_se_vazio(registro, "url", anuncio.get("url")):
                    resumo["urls_preenchidas"] += 1
                    alterado = True

                if preencher_data_se_vazia(registro, "data_publicacao", anuncio.get("data_publicacao")):
                    resumo["datas_publicacao_preenchidas"] += 1
                    alterado = True

                if preencher_se_vazio(registro, "cidade_busca", anuncio.get("municipio")):
                    resumo["cidades_busca_preenchidas"] += 1
                    alterado = True

                if preencher_se_vazio(registro, "texto_anuncio", anuncio.get("texto_anuncio")):
                    resumo["textos_preenchidos"] += 1
                    alterado = True

                if preencher_se_vazio(registro, "endereco", anuncio.get("localizacao")):
                    resumo["enderecos_preenchidos"] += 1
                    alterado = True

                novo_preco = preco_recuperavel(registro, anuncio, site)

                if novo_preco is not None and novo_preco != registro.preco_total:
                    preco_anterior = registro.preco_total
                    registro.preco_total = novo_preco
                    registro.preco_m2 = novo_preco / registro.area if registro.area is not None and registro.area > 0 else None

                    resumo["precos_recuperados"] += 1
                    alterado = True

                    print(f"[PREÇO] id={registro.id} | {site} | {preco_anterior} -> {novo_preco}")

                if alterado:
                    ids_alterados.add(registro.id)
                    pendentes += 1

                    if aplicar and pendentes >= TAMANHO_LOTE:
                        session.commit()
                        resumo["lotes_gravados"] += 1
                        print(f"[LOTE] {pendentes} alteração(ões) gravada(s).")
                        pendentes = 0

        resumo["registros_encontrados_banco"] = len(ids_encontrados)
        resumo["registros_nao_encontrados"] = len(ids_nao_encontrados)
        resumo["registros_alterados"] = len(ids_alterados)

        if aplicar:
            if pendentes > 0:
                session.commit()
                resumo["lotes_gravados"] += 1
                print(f"[LOTE] {pendentes} alteração(ões) gravada(s).")
        else:
            session.rollback()

    print("\n===== RESUMO DO BACKFILL =====")
    print(f"Modo: {'APLICAR' if aplicar else 'DRY-RUN'}")

    for chave, valor in resumo.items():
        print(f"{chave}: {valor}")

    if not aplicar:
        print("\nNenhuma alteração foi gravada.")
        print("Revise o resumo e, se estiver correto, execute novamente com --aplicar.")


def main():
    parser = argparse.ArgumentParser(
        description="Recupera dados antigos dos JSONs processados em lotes pequenos e corrige preços apenas quando houver evidência forte."
    )
    parser.add_argument(
        "--aplicar",
        action="store_true",
        help="Grava as alterações no banco. Sem esta opção, executa apenas simulação."
    )

    args = parser.parse_args()

    if not os.environ.get("DATABASE_URL"):
        raise RuntimeError("A variável de ambiente DATABASE_URL não está definida.")

    processar(aplicar=args.aplicar)


if __name__ == "__main__":
    main()
