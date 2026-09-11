import argparse
import json
import os
import re
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.connection import engine
from database.models import Anuncio
from database.repository import detectar_tipo_imovel


PASTA_PROCESSED = Path("data/processed")
PADRAO_ARQUIVO = re.compile(r"^(?P<site>[a-z0-9_-]+)_dados_(?P<data>\d{4}-\d{2}-\d{2})\.json$", re.I)

TAMANHO_LOTE = 25


def texto_valido(valor):
    if valor is None:
        return None

    texto = str(valor).strip()
    return texto or None


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
        "registros_encontrados_banco": 0,
        "registros_nao_encontrados": 0,
        "registros_alterados": 0,
        "titulos_preenchidos": 0,
        "urls_preenchidas": 0,
        "enderecos_preenchidos": 0,
        "tipos_imovel_preenchidos": 0,
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

                titulo_json = texto_valido(anuncio.get("titulo"))

                if preencher_se_vazio(registro, "titulo", titulo_json):
                    resumo["titulos_preenchidos"] += 1
                    alterado = True

                if preencher_se_vazio(registro, "url", anuncio.get("url")):
                    resumo["urls_preenchidas"] += 1
                    alterado = True

                if preencher_se_vazio(registro, "endereco", anuncio.get("localizacao")):
                    resumo["enderecos_preenchidos"] += 1
                    alterado = True

                if registro.tipo_imovel is None or not str(registro.tipo_imovel).strip():
                    tipo = detectar_tipo_imovel(titulo_json)

                    if tipo is not None:
                        registro.tipo_imovel = tipo
                        resumo["tipos_imovel_preenchidos"] += 1
                        alterado = True

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

    print("\n===== RESUMO DO BACKFILL SEGURO =====")
    print(f"Modo: {'APLICAR' if aplicar else 'DRY-RUN'}")

    for chave, valor in resumo.items():
        print(f"{chave}: {valor}")

    if not aplicar:
        print("\nNenhuma alteração foi gravada.")
        print("Revise o resumo e, se estiver correto, execute novamente com --aplicar.")


def main():
    parser = argparse.ArgumentParser(
        description="Recupera apenas título, URL, endereço e tipo do imóvel a partir dos JSONs históricos."
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
