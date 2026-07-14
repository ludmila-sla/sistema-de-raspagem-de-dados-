import hashlib
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import select

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

    if "loteamento" in titulo:
        return "Lote"

    if "lote" in titulo:
        return "Lote"

    return None


def salvar_anuncios(lista, site):

    with Session(engine) as session:

        for anuncio in lista:

            area = anuncio.get("area")
            preco = anuncio.get("preco_total")

            if (
                area is not None
                and preco is not None
                and area > 0
            ):
                preco_m2 = preco / area
            else:
                preco_m2 = None

            hash_conteudo = gerar_hash_conteudo(anuncio)

            registro = Anuncio(

                id_anuncio=anuncio.get("id_anuncio"),

                data_busca=datetime.now().date(),

                endereco=anuncio.get("localizacao"),

                area=area,

                preco_total=preco,

                preco_m2=preco_m2,

                tipo_imovel=detectar_tipo_imovel(
                    anuncio.get("titulo")
                ),

                site=site,

                cidade=anuncio.get("municipio"),

                hash_conteudo=hash_conteudo
            )

            ja_existe = session.scalar(
                select(Anuncio).where(
                    Anuncio.id_anuncio == registro.id_anuncio
                )
            )

            if ja_existe:
                continue

            session.add(registro)

        session.commit()
