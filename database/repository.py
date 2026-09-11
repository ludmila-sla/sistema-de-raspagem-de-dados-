import hashlib
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from .connection import engine
from .models import Anuncio


def gerar_hash_conteudo(anuncio):
    texto = (
        f"{anuncio.get('municipio', '')}"
        f"{anuncio.get('localizacao', '')}"
        f"{anuncio.get('area', '')}"
        f"{anuncio.get('preco_total', '')}"
        f"{anuncio.get('tipo_imovel', '')}"
    )
    return hashlib.sha256(texto.encode()).hexdigest()


def detectar_tipo_imovel(titulo):
    if not titulo:
        return None

    titulo = titulo.lower()
    if "terreno" in titulo:
        return "Terreno"
    if "loteamento" in titulo or "lote" in titulo:
        return "Lote"
    return None


def converter_data(valor):
    if not valor:
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor

    for formato in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(str(valor), formato).date()
        except ValueError:
            continue
    return None


def salvar_anuncios(lista, site, data_busca=None):
    data_lote = converter_data(data_busca) or datetime.now().date()

    with Session(engine) as session:
        for anuncio in lista:
            area = anuncio.get("area")
            preco = anuncio.get("preco_total")
            preco_m2 = preco / area if area is not None and preco is not None and area > 0 else None

            registro = Anuncio(
                id_anuncio=anuncio.get("id_anuncio"),
                data_busca=data_lote,
                data_publicacao=converter_data(anuncio.get("data_publicacao")),
                titulo=anuncio.get("titulo"),
                texto_anuncio=anuncio.get("texto_anuncio"),
                url=anuncio.get("url"),
                endereco=anuncio.get("localizacao"),
                area=area,
                preco_total=preco,
                preco_m2=preco_m2,
                tipo_imovel=detectar_tipo_imovel(anuncio.get("titulo")),
                site=site,
                cidade=anuncio.get("municipio"),
                cidade_busca=anuncio.get("municipio"),
                hash_conteudo=gerar_hash_conteudo(anuncio)
            )

            ja_existe = session.scalar(select(Anuncio).where(Anuncio.id_anuncio == registro.id_anuncio))
            if ja_existe:
                continue

            session.add(registro)

        session.commit()