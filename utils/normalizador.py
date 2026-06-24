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

def mapear_campo_sistema(termo_html):
    termo_limpo = limpar_texto(termo_html)
    
    for campo_oficial, variacoes in MAPEAMENTO_CAMPOS.items():
        for variacao in variacoes:
            variacao_limpa = limpar_texto(variacao)
            if variacao_limpa in termo_limpo:
                return campo_oficial
                
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
