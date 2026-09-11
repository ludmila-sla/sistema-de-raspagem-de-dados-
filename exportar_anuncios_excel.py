import os
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from database.connection import engine


ARQUIVO_SAIDA = Path("exports/anuncios.xlsx")


QUERY = """
SELECT
    id,
    id_anuncio,
    data_busca,
    data_publicacao,
    titulo,
    texto_anuncio,
    url,
    endereco,
    cidade,
    cidade_busca,
    area,
    preco_total,
    preco_m2,
    tipo_imovel,
    site,
    hash_conteudo,
    criado_em,
    duplicado_de_id
FROM public.anuncios
ORDER BY data_busca, site, cidade, id
"""


def formatar_data_br(valor):
    if pd.isna(valor):
        return None

    data = pd.to_datetime(valor, errors="coerce")
    if pd.isna(data):
        return None

    return data.strftime("%d/%m/%Y")


def exportar():
    if not os.environ.get("DATABASE_URL"):
        raise RuntimeError("A variável DATABASE_URL não está definida.")

    ARQUIVO_SAIDA.parent.mkdir(parents=True, exist_ok=True)

    with engine.connect() as conexao:
        df = pd.read_sql(text(QUERY), conexao)

    for coluna in ("data_busca", "data_publicacao", "criado_em"):
        if coluna in df.columns:
            df[coluna] = df[coluna].apply(formatar_data_br)

    with pd.ExcelWriter(ARQUIVO_SAIDA, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="anuncios", index=False)

        planilha = writer.book["anuncios"]
        planilha.freeze_panes = "A2"
        planilha.auto_filter.ref = planilha.dimensions

        for coluna in planilha.columns:
            maior = max(len(str(celula.value or "")) for celula in coluna)
            planilha.column_dimensions[coluna[0].column_letter].width = min(maior + 2, 60)

    print(f"Arquivo gerado: {ARQUIVO_SAIDA}")
    print(f"Registros exportados: {len(df)}")


if __name__ == "__main__":
    exportar()
