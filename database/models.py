from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, Date, DateTime, Float, Integer, String, Text, func


class Base(DeclarativeBase):
    pass


class Anuncio(Base):
    __tablename__ = "anuncios"

    id = Column(Integer, primary_key=True)
    id_anuncio = Column(String, unique=True, nullable=False)
    data_busca = Column(Date)
    data_publicacao = Column(Date)
    titulo = Column(Text)
    texto_anuncio = Column(Text)
    url = Column(Text)
    endereco = Column(Text)
    area = Column(Float)
    preco_total = Column(Float)
    preco_m2 = Column(Float)
    tipo_imovel = Column(String)
    site = Column(String)
    cidade = Column(String)
    cidade_busca = Column(String)
    hash_conteudo = Column(String)
    criado_em = Column(DateTime, server_default=func.now())


class Log(Base):
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True)
    data = Column(DateTime, server_default=func.now())
    modulo = Column(String)
    nivel = Column(String)
    mensagem = Column(Text)