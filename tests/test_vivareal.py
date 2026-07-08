import unittest
import hashlib
from scrapers.vivareal import gerar_url_vivareal
from processar_dados import processar_html_vivareal

class TestVivaRealTerrenos(unittest.TestCase):

    def test_gerar_url_vivareal_terrenos(self):
        """Valida se a URL gerada aponta estritamente para a seção de lotes e terrenos."""
        url = gerar_url_vivareal("presidente-prudente")
        self.assertEqual(url, "https://www.vivareal.com.br/venda/sp/presidente-prudente/lote-terreno_secao/")

    def test_processar_html_vivareal_terreno_schema(self):
        """Testa o parser mapeando chaves nulas e gerando ID via MD5."""
        url_teste = "https://www.vivareal.com.br/imovel/lote-terreno-id-123456/"
        id_esperado = hashlib.md5(url_teste.strip().encode('utf-8')).hexdigest()

        html_simulado = f"""
        <html>
        <head>
            <script type="application/ld+json">{{
              "@context":"https://schema.org",
              "@type":"Product",
              "name":"Terreno Residencial à Venda",
              "floorSize": {{"@type": "QuantitativeValue", "value": 250}},
              "offers":{{
                "@type":"Offer",
                "url":"{url_teste}",
                "priceCurrency":"BRL",
                "price":120000
              }}
            }}</script>
        </head>
        </html>
        """
        resultado = processar_html_vivareal(html_simulado, "Bauru")
        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0]["id_anuncio"], id_esperado)
        self.assertEqual(resultado[0]["area"], 250.0)
        self.assertEqual(resultado[0]["preco_total"], 120000.0)

if __name__ == "__main__":
    unittest.main()
