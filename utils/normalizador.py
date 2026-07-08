import re
import unicodedata

MAPEAMENTO_CAMPOS = {
    "area": [
        "área", "área útil", "área total", "tamanho", "m²", "metros quadrados", 
        "área terreno", "dimensão"
    ],
    "preco_total": [
        "preço", "valor", "preço total", "valor total", "venda", "valor de venda"
    ],
    "condominio": [
        "condomínio", "valor condomínio", "taxa condominial", "condo"
    ],
    "iptu": [
        "iptu", "iptu anual", "iptu mensal", "valor iptu"
    ],
    "localizacao": [
        "localização", "endereço", "bairro", "logradouro", "zona"
    ]
}

def limpar_texto(texto):
    if not texto:
        return ""
    texto = re.sub(r'\s+', ' ', str(texto).strip().lower())
    texto = ''.join(c for c in unicodedata.normalize('NFKD', texto) if not unicodedata.combining(c))
    return texto

def mapear_campo_sistema(texto_html):
    if not texto_html:
        return None
    texto = texto_html.lower().strip()
    
    if "metro" in texto or "m²" in texto or "area" in texto or "tamanho" in texto:
        return "area"
        
    if "preço" in texto or "preco" in texto or "valor" in texto:
        return "preco_total"
        
    if "condomínio" in texto or "condominio" in texto:
        return "condominio"
        
    if "iptu" in texto:
        return "iptu"
        
    if "localização" in texto or "localizacao" in texto or "endereço" in texto:
        return "localizacao"
        
    return None

def tratar_valor_numerico(campo, valor_texto):
    if not valor_texto:
        return None
        
    texto_limpo = re.sub(r'[^\d,]', '', str(valor_texto))
    
    if not texto_limpo:
        return None
        
    try:
        if "," in texto_limpo:
            texto_limpo = texto_limpo.replace(".", "").replace(",", ".")
        return float(texto_limpo)
    except ValueError:
        return None
