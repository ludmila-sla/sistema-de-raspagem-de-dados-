import unittest
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
                        "description": "Casa Térrea à Venda com 4 Quartos por R$-189.990-00 em Local Privilegiado... de 110 m².",
                        "url": "https://www.imovelweb.com.br/propriedades/casa-a-venda-110-m-por-r$-189.990-00-nucleo-3029672676.html",
                        "image": "https://imgbr.imovelwebcdn.com/avisos/2/30/29/67/26/76/720x532/6223681127.jpg",
                        "datePosted": "6/16/26",
                        "contentLocation": {
                            "type": "Place",
                            "name": "Núcleo Residencial Beija-Flor"
                        }
                    }
                ]
            }
            </script>
        </head>
        <body></body>
        </html>
        """
        resultado = processar_html_imovelweb(html_simulado, "Bauru")

        self.assertEqual(len(resultado), 1)
        anuncio = resultado[0]
        
        self.assertEqual(anuncio["municipio"], "Bauru")
        self.assertEqual(anuncio["titulo"], "ZUCCARO IMOVEIS")
        self.assertEqual(anuncio["area"], 110.0)
        self.assertEqual(anuncio["preco_total"], 189990.0)
        self.assertEqual(anuncio["id_anuncio"], "2432ec80b09c7cecc54f9bafcf39bf94")


   

if __name__ == "__main__":
    unittest.main()
