import argparse
import json
import os
import re
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.connection import engine
from database.models import Anuncio
from utils.normalizador import tratar_valor_numerico


PASTA_PROCESSED = Path("data/processed")
PADRAO_ARQUIVO = re.compile(r"^(?P<site>[a-z0-9_-]+)_dados_(?P<data>\d{4}-\d{2}-\d{2})\.json$", re.I)
PADRAO_PRECO_TEXTO = re.compile(r"R\$\s*([\d.]+(?:,\d{1,2})?)", re.I)


def texto_valido(valor):
    if valor is None:
        return None

    texto = str(valor).strip()
    return texto or None


def extrair_preco_texto(*valores):
    for valor in valores:
        texto = texto_valido(valor)
        if not texto:
            continue

        match = PADRAO_PRECO_TEXTO.search(texto)
        if not match:
            continue

        preco = tratar_valor_numerico("preco_total", match.group(1))
        if preco is not None and preco > 0:
            return preco

    return None


def preco_recuperavel(registro, anuncio):
    preco_atual = registro.preco_total

    # Primeiro tenta recuperar o valor escrito por extenso no título/texto.
    preco_texto = extrair_preco_texto(
        anuncio.get("titulo"),
        anuncio.get("texto_anuncio")
    )

    if preco_texto is not None:
        if preco_atual is None:
            return preco_texto

        # Corrige valores antigos como 110.0 quando o texto diz R$ 110.000,00.
        if preco_atual < 10000 <= preco_texto:
            return preco_texto

    # Se o JSON já possuir um preço plausível, pode preencher apenas campos NULL.
    preco_json = anuncio.get("preco_total")
    if preco_atual is None and isinstance(preco_json, (int, float)) and preco_json >= 10000:
        return float(preco_json)

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


def processar(aplicar=False):
    resumo = {
        "arquivos": 0,
        "itens_json": 0,
        "encontrados_banco": 0,
        "nao_encontrados": 0,
        "registros_alterados": 0,
        "precos_recuperados": 0,
        "titulos_preenchidos": 0,
        "urls_preenchidas": 0,
        "cidades_busca_preenchidas": 0,
        "textos_preenchidos": 0,
        "enderecos_preenchidos": 0
    }

    vistos = set()

    with Session(engine) as session:
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

                chave = (site, id_anuncio)
                if chave in vistos:
                    continue

                registro = session.scalar(
                    select(Anuncio).where(Anuncio.id_anuncio == id_anuncio)
                )

                if registro is None:
                    resumo["nao_encontrados"] += 1
                    continue

                vistos.add(chave)
                resumo["encontrados_banco"] += 1
                alterado = False

                if preencher_se_vazio(registro, "titulo", anuncio.get("titulo")):
                    resumo["titulos_preenchidos"] += 1
                    alterado = True

                if preencher_se_vazio(registro, "url", anuncio.get("url")):
                    resumo["urls_preenchidas"] += 1
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

                novo_preco = preco_recuperavel(registro, anuncio)

                if novo_preco is not None and novo_preco != registro.preco_total:
                    preco_anterior = registro.preco_total
                    registro.preco_total = novo_preco
                    registro.preco_m2 = (
                        novo_preco / registro.area
                        if registro.area is not None and registro.area > 0
                        else None
                    )

                    resumo["precos_recuperados"] += 1
                    alterado = True

                    print(
                        f"[PREÇO] id={registro.id} | {site} | "
                        f"{preco_anterior} -> {novo_preco}"
                    )

                if alterado:
                    resumo["registros_alterados"] += 1

        if aplicar:
            session.commit()
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
        description="Recupera dados antigos dos JSONs processados e corrige preços quando houver evidência no texto."
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
