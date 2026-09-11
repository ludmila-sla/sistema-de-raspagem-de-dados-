import argparse
import json
import os
import re
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database.connection import engine
from database.models import Anuncio
from database.repository import converter_data, detectar_tipo_imovel


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
        "enderecos_preenchidos": 0,
        "tipos_imovel_preenchidos": 0,
        "textos_preenchidos": 0,
        "datas_publicacao_preenchidas": 0
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

                registro = session.scalar(select(Anuncio).where(Anuncio.id_anuncio == id_anuncio))

                if registro is None:
                    ids_nao_encontrados.add(id_anuncio)
                    continue

                ids_encontrados.add(id_anuncio)
                alterado = False

                endereco = texto_valido(anuncio.get("localizacao"))
                if (registro.endereco is None or not registro.endereco.strip()) and endereco:
                    registro.endereco = endereco
                    resumo["enderecos_preenchidos"] += 1
                    alterado = True

                if registro.tipo_imovel is None or not str(registro.tipo_imovel).strip():
                    tipo = detectar_tipo_imovel(texto_valido(anuncio.get("titulo")))
                    if tipo:
                        registro.tipo_imovel = tipo
                        resumo["tipos_imovel_preenchidos"] += 1
                        alterado = True

                texto_anuncio = texto_valido(anuncio.get("texto_anuncio"))
                if (registro.texto_anuncio is None or not registro.texto_anuncio.strip()) and texto_anuncio:
                    registro.texto_anuncio = texto_anuncio
                    resumo["textos_preenchidos"] += 1
                    alterado = True

                if registro.data_publicacao is None:
                    data_publicacao = converter_data(anuncio.get("data_publicacao"))
                    if data_publicacao:
                        registro.data_publicacao = data_publicacao
                        resumo["datas_publicacao_preenchidas"] += 1
                        alterado = True

                if alterado:
                    ids_alterados.add(registro.id)

        resumo["registros_encontrados"] = len(ids_encontrados)
        resumo["registros_nao_encontrados"] = len(ids_nao_encontrados)
        resumo["registros_alterados"] = len(ids_alterados)

        session.flush()

        total_depois_flush = session.scalar(select(func.count()).select_from(Anuncio))
        print(f"Registros após os UPDATEs, antes do commit: {total_depois_flush}")

        if total_depois_flush != total_antes:
            session.rollback()
            raise RuntimeError(
                f"CONTAGEM ALTERADA: antes={total_antes}, depois={total_depois_flush}. "
                "Rollback executado."
            )

        if aplicar:
            session.commit()

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
        description=(
            "Backfill conservador dos campos recuperáveis: endereco, tipo_imovel, "
            "texto_anuncio e data_publicacao."
        )
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
