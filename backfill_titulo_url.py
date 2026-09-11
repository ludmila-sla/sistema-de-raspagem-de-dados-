import argparse
import json
import os
import re
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database.connection import engine
from database.models import Anuncio


PASTA_PROCESSED = Path("data/processed")
PADRAO_ARQUIVO = re.compile(r"^[a-z0-9_-]+_dados_\d{4}-\d{2}-\d{2}\.json$", re.I)


def texto_valido(valor):
    if valor is None:
        return None

    texto = str(valor).strip()
    return texto or None


def carregar_arquivos():
    if not PASTA_PROCESSED.exists():
        raise FileNotFoundError(f"Pasta não encontrada: {PASTA_PROCESSED}")

    return [
        caminho
        for caminho in sorted(PASTA_PROCESSED.glob("*_dados_*.json"))
        if PADRAO_ARQUIVO.match(caminho.name)
    ]


def carregar_json(caminho):
    with caminho.open("r", encoding="utf-8") as arquivo:
        dados = json.load(arquivo)

    if not isinstance(dados, list):
        raise ValueError(f"{caminho} não contém uma lista de anúncios.")

    return dados


def processar(aplicar=False):
    resumo = {
        "arquivos": 0,
        "itens_json": 0,
        "registros_encontrados": 0,
        "registros_nao_encontrados": 0,
        "registros_alterados": 0,
        "titulos_preenchidos": 0,
        "urls_preenchidas": 0
    }

    ids_encontrados = set()
    ids_nao_encontrados = set()
    ids_alterados = set()

    with Session(engine, autoflush=False) as session:
        total_antes = session.scalar(select(func.count()).select_from(Anuncio))

        print(f"Registros antes do backfill: {total_antes}")

        if not total_antes:
            raise RuntimeError("A tabela anuncios está vazia. Backfill cancelado.")

        for caminho in carregar_arquivos():
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

                registro = session.scalar(
                    select(Anuncio).where(Anuncio.id_anuncio == id_anuncio)
                )

                if registro is None:
                    ids_nao_encontrados.add(id_anuncio)
                    continue

                ids_encontrados.add(id_anuncio)
                alterado = False

                titulo = texto_valido(anuncio.get("titulo"))
                url = texto_valido(anuncio.get("url"))

                if (registro.titulo is None or not registro.titulo.strip()) and titulo:
                    registro.titulo = titulo
                    resumo["titulos_preenchidos"] += 1
                    alterado = True

                if (registro.url is None or not registro.url.strip()) and url:
                    registro.url = url
                    resumo["urls_preenchidas"] += 1
                    alterado = True

                if alterado:
                    ids_alterados.add(registro.id)

        resumo["registros_encontrados"] = len(ids_encontrados)
        resumo["registros_nao_encontrados"] = len(ids_nao_encontrados)
        resumo["registros_alterados"] = len(ids_alterados)

        # Envia os UPDATEs ao PostgreSQL, mas ainda NÃO confirma a transação.
        session.flush()

        total_depois_flush = session.scalar(select(func.count()).select_from(Anuncio))

        print(f"Registros após os UPDATEs, antes do commit: {total_depois_flush}")

        if total_depois_flush != total_antes:
            session.rollback()
            raise RuntimeError(
                f"CONTAGEM ALTERADA: antes={total_antes}, "
                f"depois={total_depois_flush}. Rollback executado."
            )

        if aplicar:
            session.commit()

            # Validação em uma nova transação, após o commit.
            total_depois_commit = session.scalar(select(func.count()).select_from(Anuncio))
            print(f"Registros após o commit: {total_depois_commit}")

            if total_depois_commit != total_antes:
                raise RuntimeError(
                    f"ALERTA: após o commit a tabela passou de "
                    f"{total_antes} para {total_depois_commit} registros."
                )
        else:
            session.rollback()
            print("DRY-RUN: rollback executado. Nenhuma alteração foi gravada.")

    print("\n===== RESUMO =====")
    print(f"Modo: {'APLICAR' if aplicar else 'DRY-RUN'}")

    for chave, valor in resumo.items():
        print(f"{chave}: {valor}")


def main():
    parser = argparse.ArgumentParser(
        description="Backfill conservador: preenche somente titulo e url."
    )
    parser.add_argument(
        "--aplicar",
        action="store_true",
        help="Confirma a transação. Sem esta opção, executa dry-run com rollback."
    )
    args = parser.parse_args()

    if not os.environ.get("DATABASE_URL"):
        raise RuntimeError("A variável DATABASE_URL não está definida.")

    processar(aplicar=args.aplicar)


if __name__ == "__main__":
    main()
