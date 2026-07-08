import unittest
import json
from processar_dados import processar_html_imovelweb
from utils.normalizador import tratar_valor_numerico

class TestPipelineImovelweb(unittest.TestCase):

    def setUp(self):

        self.html_exemplo = """
        <!DOCTYPE html>
        <html>
        <head>
            <script type="application/ld+json">
            {
                "mainEntity": [
                    {
                        "type": "RealEstateListing",
                        "name": "ZUCCARO IMOVEIS ",
                        "description": "Corretor: David Willian Tel.: (11) Ver dados. creci: Ver dados-F. Casa Térrea à Venda com 4 Quartos em Local Privilegiado. Esta casa totalmente térrea oferece 4 quartos arejados e 2 banheiros completos. O amplo quintal tem espaço para até 5 carros e uma área gourmet, além de ser totalmente coberto por laje, permitindo a construção de um segundo piso, o que valoriza ainda mais o imóvel. Localizada em um bairro tranquilo e privilegiado, a casa fica próxima a diversos comércios, escolas e um posto de saúde, com fácil acesso à Rodovia Marechal Rondon. Formas de Pagamento: Aceitamos pagamento à vista, financiamento ou permuta (somente com imóveis em Guarulhos-sp). Desde 1996, a Zuccaro Imóveis atua na venda, compra, locação e lançamento de imóveis, oferecendo serviços de alta qualidade e um atendimento diferenciado. Nosso time qualificado tem cativado e fidelizado constantemente novos clientes. Corretor: David Willian Tel.: (11) Ver dados. creci: Ver dados-F - 15062026",
                        "url": "https://www.imovelweb.com.br/propriedades/casa-a-venda-110-m-por-r$-189.990-00-nucleo-3029672676.html",
                        "image": "https://imgbr.imovelwebcdn.com/avisos/2/30/29/67/26/76/720x532/6223681127.jpg",
                        "datePosted": "6/16/26",
                        "contentLocation": {
                            "type": "Place",
                            "name": "Núcleo Residencial Beija-Flor"
                        },
                        "countryOfOrigin": {
                            "type": "Country",
                            "name": "Brasil"
                        }
                    }
                ]
            }
            </script>
        </head>
        <body></body>
        </html>
        """

    def test_normalizador_valores_numericos_imovelweb(self):
        """Garante a higienização correta dos dados via RegExp rodando na utilidade do sistema."""

        self.assertEqual(tratar_valor_numerico("preco_total", "189.990-00"), 189990.0)
        self.assertEqual(tratar_valor_numerico("area", "110"), 110.0)
        self.assertEqual(tratar_valor_numerico("condominio", "0.0"), 0.0)

    def test_extraicao_completa_anuncio_imovelweb(self):
        """Valida o mapeamento do dicionário final gerado a partir do Schema JSON-LD bruto."""
        dados_processados = processar_html_imovelweb(self.html_exemplo, "Bauru")
        

        self.assertEqual(len(dados_processados), 1)
        
        anuncio = dados_processados[0]
        

        self.assertEqual(anuncio["id_anuncio"], "4850fa3fa041b6cb1e8b233a7e53f191")
        self.assertEqual(anuncio["municipio"], "Bauru")
        self.assertEqual(anuncio["titulo"], "ZUCCARO IMOVEIS")
        self.assertEqual(anuncio["localizacao"], "Núcleo Residencial Beija-Flor")
        self.assertEqual(anuncio["url"], "https://www.imovelweb.com.br/propriedades/casa-a-venda-110-m-por-r$-189.990-00-nucleo-3029672676.html")
        

        self.assertEqual(anuncio["preco_total"], 189990.0)
        self.assertEqual(anuncio["area"], 110.0)
        self.assertEqual(anuncio["condominio"], 0.0)
        self.assertEqual(anuncio["iptu"], 0.0)

if __name__ == "__main__":
    unittest.main()
