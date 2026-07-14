from sqlalchemy.orm import Session
from sqlalchemy import select
from .connection import engine
from .models import *
import hashlib

def gerar_grupo_duplicado(anuncio):
    texto = (
        f"{anuncio['cidade']}"
        f"{anuncio['endereco']}"
        f"{anuncio['area']}"
        f"{anuncio['preco_total']}"
    )

    return hashlib.sha256(
        texto.encode()
    ).hexdigest()

def salvar_anuncios(lista):
  with Session(engine) as session:

    for anuncio in lista:
      if anuncio["area"] and anuncio["preco_total"]:
        anuncio["preco_m2"] = (
        anuncio["preco_total"] / anuncio["area"]
    )
      else:
        anuncio["preco_m2"] = None
        
      anuncio["grupo_duplicado"] = gerar_grupo_duplicado(anuncio)
      registro = Anuncio(
        id_anuncio=anuncio["id_anuncio"],
        data_busca=anuncio["data_busca"],
        endereco=anuncio["endereco"],
        area=anuncio["area"],
        preco_total=anuncio["preco_total"],
        preco_m2=anuncio["preco_m2"],
        tipo_imovel=anuncio["tipo_imovel"],
        site=anuncio["site"],
        cidade=anuncio["cidade"],
        grupo_duplicado=anuncio["grupo_duplicado"])

      ja_existe = session.scalar(
        select(Anuncio).where(
          Anuncio.id_anuncio == anuncio["id_anuncio"]
    )
)
      if ja_existe:
        continue
      session.add(registro)
      
session.commit()
