import os
import tempfile
import unittest
from datetime import date

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from bs4 import BeautifulSoup
from database.connection import engine
from database.models import Anuncio, Base
from database.repository import salvar_anuncios
from processar_dados import extrair_anuncio_olx, extrair_data_publicacao_olx, processar_html_imovelweb, processar_html_vivareal, processar_html_zap
from sqlalchemy import select
from sqlalchemy.orm import Session


class TestProcessamento(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(engine)

    def setUp(self):
        with Session(engine) as session:
            session.query(Anuncio).delete()
            session.commit()

    def test_olx_extrai_data_texto_titulo_url_e_localizacao(self):
        html = '''
        <section class="olx-adcard">
            <a class="olx-adcard__link" href="https://sp.olx.com.br/anuncio/123">
                <h2>Terreno em Piratininga</h2>
            </a>
            <div class="olx-adcard__detail" aria-label="167 metros quadrados">167m²</div>
            <h3 class="olx-adcard__price">R$ 130.000</h3>
            <p class="olx-adcard__location">Vila Santa Maria11 de jul, 01:49</p>
        </section>
        '''
        card = BeautifulSoup(html, "html.parser").select_one("section")
        anuncio = extrair_anuncio_olx(card, "Piratininga", "2026-07-14")

        self.assertEqual(anuncio["titulo"], "Terreno em Piratininga")
        self.assertEqual(anuncio["url"], "https://sp.olx.com.br/anuncio/123")
        self.assertEqual(anuncio["localizacao"], "Vila Santa Maria")
        self.assertEqual(anuncio["data_publicacao"], date(2026, 7, 11))
        self.assertEqual(anuncio["area"], 167.0)
        self.assertEqual(anuncio["preco_total"], 130000.0)
        self.assertIn("Terreno em Piratininga", anuncio["texto_anuncio"])
        self.assertIn("R$ 130.000", anuncio["texto_anuncio"])

    def test_olx_trata_virada_de_ano(self):
        data_publicacao, localizacao = extrair_data_publicacao_olx("Centro28 de dez, 10:30", "2027-01-05")
        self.assertEqual(data_publicacao, date(2026, 12, 28))
        self.assertEqual(localizacao, "Centro")

    def test_olx_trata_hoje_e_ontem(self):
        hoje, local_hoje = extrair_data_publicacao_olx("CentroHoje, 10:30", "2026-07-14")
        ontem, local_ontem = extrair_data_publicacao_olx("CentroOntem, 10:30", "2026-07-14")
        self.assertEqual(hoje, date(2026, 7, 14))
        self.assertEqual(ontem, date(2026, 7, 13))
        self.assertEqual(local_hoje, "Centro")
        self.assertEqual(local_ontem, "Centro")

    def test_zap_salva_texto_e_data_quando_existirem_no_jsonld(self):
        html = '''
        <script type="application/ld+json">
        {"@type":"ItemList","itemListElement":[{"item":{"name":"Terreno ZAP","description":"Terreno amplo próximo ao centro","url":"https://zap.com.br/1","datePosted":"2026-07-10","floorSize":{"value":200},"offers":{"price":300000},"address":{"addressLocality":"Bauru"}}}]}
        </script>
        '''
        anuncio = processar_html_zap(html, "Bauru")[0]
        self.assertEqual(anuncio["texto_anuncio"], "Terreno amplo próximo ao centro")
        self.assertEqual(anuncio["data_publicacao"], date(2026, 7, 10))

    def test_vivareal_salva_texto_e_data(self):
        html = '''
        <script type="application/ld+json">
        {"@type":"Product","name":"Terreno VivaReal","description":"Texto visível do anúncio","url":"https://vivareal.com.br/1","datePosted":"2026-07-09","floorSize":{"value":150},"offers":{"price":250000},"address":{"addressLocality":"Bauru"}}
        </script>
        '''
        anuncio = processar_html_vivareal(html, "Bauru")[0]
        self.assertEqual(anuncio["texto_anuncio"], "Texto visível do anúncio")
        self.assertEqual(anuncio["data_publicacao"], date(2026, 7, 9))

    def test_imovelweb_usa_texto_completo_do_card(self):
        html = '''
        <div data-posting-type="PROPERTY" data-id="123">
            <a href="/propriedades/123.html">abrir</a>
            <h2 data-qa="POSTING_CARD_TITLE">Terreno Imovelweb</h2>
            <div data-qa="POSTING_CARD_DESCRIPTION">Excelente terreno</div>
            <div data-qa="POSTING_CARD_PRICE">R$ 180.000</div>
            <div data-qa="POSTING_CARD_FEATURES">180 m²</div>
            <div data-qa="POSTING_CARD_LOCATION">Bauru, Centro</div>
            <time datetime="2026-07-08">8 de julho</time>
        </div>
        '''
        anuncio = processar_html_imovelweb(html, "Bauru")[0]
        self.assertEqual(anuncio["titulo"], "Terreno Imovelweb")
        self.assertEqual(anuncio["url"], "https://www.imovelweb.com.br/propriedades/123.html")
        self.assertEqual(anuncio["data_publicacao"], date(2026, 7, 8))
        self.assertIn("Excelente terreno", anuncio["texto_anuncio"])

    def test_repository_salva_novos_campos_e_data_do_lote(self):
        salvar_anuncios([{
            "id_anuncio": "abc",
            "municipio": "Piratininga",
            "titulo": "Terreno",
            "texto_anuncio": "Terreno 100 m² R$ 100.000",
            "url": "https://exemplo.com/abc",
            "data_publicacao": "11/07/2026",
            "localizacao": "Vila Santa Maria",
            "area": 100.0,
            "preco_total": 100000.0
        }], "olx", "2026-07-14")

        with Session(engine) as session:
            anuncio = session.scalar(select(Anuncio).where(Anuncio.id_anuncio == "abc"))
            self.assertEqual(anuncio.data_busca, date(2026, 7, 14))
            self.assertEqual(anuncio.data_publicacao, date(2026, 7, 11))
            self.assertEqual(anuncio.cidade_busca, "Piratininga")
            self.assertEqual(anuncio.titulo, "Terreno")
            self.assertEqual(anuncio.texto_anuncio, "Terreno 100 m² R$ 100.000")
            self.assertEqual(anuncio.url, "https://exemplo.com/abc")


if __name__ == "__main__":
    unittest.main()
