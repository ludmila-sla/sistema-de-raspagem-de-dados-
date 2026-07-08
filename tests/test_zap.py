import os
import json
import pytest
from scrapers.zap import normalizar_slug_zap
from processar_dados import processar_html_zap

def test_normalizar_slug_zap():
    """Valida se a conversão de nomes de cidades para o padrão de URL do Zap funciona."""
    assert normalizar_slug_zap("São José dos Campos") == "sao-jose-dos-campos"
    assert normalizar_slug_zap("Bauru") == "bauru"

def test_processar_html_zap_com_dados_reais_schema():
    """Testa o parser usando o fragmento real de LD+JSON fornecido pelo site do Zap."""
  
    schema_mock = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": "Imóveis para alugar em Bauru - SP",
        "numberOfItems": 30,
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": 1,
                "item": {
                    "@type": "Apartment",
                    "@id": "2883807011",
                    "name": "Apartamento para alugar com 47 m², 2 quartos, 1 banheiro, 1 vaga",
                    "url": "https://www.zapimoveis.com.br/imovel/aluguel-apartamento-2-quartos-id-2883807011/",
                    "description": "Apartamento funcional e bem localizado...",
                    "address": {
                        "@type": "PostalAddress",
                        "addressLocality": "Bauru",
                        "addressRegion": "SP"
                    },
                    "floorSize": {
                        "@type": "QuantitativeValue",
                        "value": 47
                    },
                    "offers": {
                        "@type": "Offer",
                        "price": 1500,
                        "additionalProperty": {
                            "@type": "PropertyValue",
                            "name": "Condominium Fee",
                            "value": 361
                        }
                    }
                }
            }
        ]
    }

    html_simulado = f"""
    <html>
        <head>
            <script type="application/ld+json">
                {json.dumps(schema_mock)}
            </script>
        </head>
        <body></body>
    </html>
    """

    resultado = processar_html_zap(html_simulado, "Bauru")

    assert len(resultado) == 1
    anuncio = resultado[0]
    
    assert anuncio["municipio"] == "Bauru"
    assert anuncio["titulo"] == "Apartamento para alugar com 47 m², 2 quartos, 1 banheiro, 1 vaga"
    assert anuncio["area"] == 47.0
    assert anuncio["preco_total"] == 1500.0
    assert anuncio["condominio"] == 361.0
    assert anuncio["id_anuncio"] is not None
