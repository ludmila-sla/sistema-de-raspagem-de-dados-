import unittest
from bs4 import BeautifulSoup
from processar_dados import extrair_anuncio_olx
from utils.normalizador import mapear_campo_sistema, tratar_valor_numerico

class TestPipelineOLX(unittest.TestCase):

    def setUp(self):
        self.html_exemplo = """
        <section class="olx-adcard olx-adcard__horizontal  undefined" data-mode="horizontal">
            <div class="olx-adcard__content" data-mode="horizontal">
                <div class="olx-adcard__topbody" data-mode="horizontal">
                    <a data-testid="adcard-link" class="olx-adcard__link" title="Terreno a venda no Pq. Viaduto" href="https://sp.olx.com.br/regiao-de-bauru-e-marilia/terrenos/terreno-a-venda-no-pq-viaduto-1512978359">
                        <h2 class="typo-body-large olx-adcard__title font-semibold">Terreno a venda no Pq. Viaduto</h2>
                    </a>
                    <div class="">
                        <div class="olx-adcard__details">
                            <div class="olx-adcard__detail" aria-label="167 metros quadrados">
                                167m²
                            </div>
                        </div>
                    </div>
                </div>
                <div class="olx-adcard__mediumbody">
                    <h3 class="typo-body-large olx-adcard__price font-semibold">R$ 130.000</h3>
                </div>
                <div class="olx-adcard__bottombody">
                    <div class="olx-adcard__location-date">
                        <p class="typo-caption olx-adcard__location">Bauru, Parque Viaduto</p>
                    </div>
                </div>
            </div>
        </section>
        """
        self.soup = BeautifulSoup(self.html_exemplo, "html.parser")
        self.card = self.soup.select_one("section.olx-adcard")

        
        resultado = processar_html_olx(html_simulado, "Bauru")

        self.assertEqual(len(resultado), 1)
        anuncio = resultado[0]

        self.assertEqual(anuncio["id_anuncio"], "ef77c2a78f14b6fc531bd098ffb19b6e")
        self.assertEqual(anuncio["municipio"], "Bauru")
        self.assertEqual(anuncio["area"], 167.0)
        self.assertEqual(anuncio["preco_total"], 130000.0)


if __name__ == "__main__":
    unittest.main()
