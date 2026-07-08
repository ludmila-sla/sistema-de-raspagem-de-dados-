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

    def test_normalizador_valores_numericos_imovelweb(self):
        """Testa o utilitário com entrada já higienizada."""
        self.assertEqual(tratar_valor_numerico("preco_total", "189.990,00"), 189990.0)
        self.assertEqual(tratar_valor_numerico("area", "110"), 110.0)

    def test_extraicao_completa_anuncio_imovelweb(self):
        """Valida o ciclo completo do parser corrigindo o hífen em tempo de execução."""
        dados_processados = processar_html_imovelweb(self.html_exemplo, "Bauru")
        
        self.assertEqual(len(dados_processados), 1)
        anuncio = dados_processados[0]
        
        self.assertEqual(anuncio["id_anuncio"], "2432ec80b09c7cecc54f9bafcf39bf94")
        self.assertEqual(anuncio["municipio"], "Bauru")
        self.assertEqual(anuncio["titulo"], "ZUCCARO IMOVEIS")

        self.assertEqual(anuncio["preco_total"], 189990.0)
        self.assertEqual(anuncio["area"], 110.0)

if __name__ == "__main__":
    unittest.main()
