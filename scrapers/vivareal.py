import json
from bs4 import BeautifulSoup

def extract_listings(html_content):
    """
    Varre o HTML bruto do VivaReal procurando blocos <script type="application/ld+json">
    e filtra apenas os nós do tipo 'Product'.
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        scripts = soup.find_all('script', type='application/ld+json')
        extracted_data = []
        
        for script in scripts:
            if not script.string:
                continue
            try:
                content = json.loads(script.string)

                if content.get("@type") == "Product":
                    extracted_data.append({
                        "provider": "VivaReal",
                        "title": content.get("name", "").strip(),
                        "description": content.get("description", "").strip(),
                        "sku": content.get("sku", ""),
                        "images": content.get("image", []),
                        "price": content.get("offers", {}).get("price", None),
                        "currency": content.get("offers", {}).get("priceCurrency", ""),
                        "url": content.get("offers", {}).get("url", "")
                    })
            except json.JSONDecodeError:
                continue
                
        return extracted_data
        
    except Exception as e:
        return {"error": f"Erro ao processar HTML do VivaReal: {str(e)}"}
