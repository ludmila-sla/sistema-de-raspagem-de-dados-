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

    def test_normalizador_valores_numericos(self):
        self.assertEqual(tratar_valor_numerico("preco_total", "R$ 130.000"), 130000.0)
        self.assertEqual(tratar_valor_numerico("area", "167m²"), 167.0)
        self.assertEqual(tratar_valor_numerico("area", "Apenas texto"), None)

    def test_normalizador_mapeamento_campos(self):
        self.assertEqual(mapear_campo_sistema("167 metros quadrados"), "area")
        self.assertEqual(mapear_campo_sistema("Preço total"), "preco_total")
        self.assertEqual(mapear_campo_sistema("Campo Inexistente"), None)

    def test_extraicao_completa_anuncio(self):
        """Testa se a função extrair_anuncio_olx parseia o HTML real corretamente"""
        
        # DEBUG 1: Vamos ver se o seletor principal está achando o card
        print("\n=== DEBUG: CASO O CARD SEJA ENCONTRADO ===")
        print(f"Objeto card é None? {self.card is None}")
        if self.card:
            print(f"Classes encontradas no card: {self.card.get('class')}")
            
            # DEBUG 2: Vamos ver se ele acha o link dentro do card
            link = self.card.select_one("a[class*='olx-adcard__link']")
            print(f"Link encontrado: {link}")
            if link:
                print(f"Href do link: {link.get('href')}")

        dados = extrair_anuncio_olx(self.card, "Bauru")
        
        print("\n=== DEBUG: DICIONÁRIO RETORNADO PELA FUNÇÃO ===")
        print(dados)
        print("==============================================\n")
        
        # Validações estritas dos dados extraídos
        self.assertEqual(dados["id_anuncio"], "1512978359")
        self.assertEqual(dados["municipio"], "Bauru")
        self.assertEqual(dados["preco_total"], 130000.0)
        self.assertEqual(dados["area"], 167.0)
        self.assertEqual(dados["localizacao"], "Bauru, Parque Viaduto")
        self.assertTrue(dados["url"].endswith("1512978359"))

if __name__ == "__main__":
    unittest.main()
