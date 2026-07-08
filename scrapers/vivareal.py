import unicodedata
import re

def normalizar_slug_vivareal(cidade: str) -> str:
    """
    Remove acentos, caracteres especiais e substitui espaços por hifens.
    Exemplo: "São José dos Campos" -> "sao-jose-dos-campos"
    """
    cidade_norm = unicodedata.normalize('NFKD', cidade)
    cidade_norm = "".join([c for c in cidade_norm if not unicodedata.combining(c)])
    cidade_norm = cidade_norm.lower().strip()
    cidade_norm = re.sub(r'[^a-z0-9\s-]', '', cidade_norm)
    cidade_norm = re.sub(r'[\s-]+', '-', cidade_norm)
    return cidade_norm

def gerar_url_vivareal(cidade: str, tipo_contrato: str = "aluguel", tipo_imovel: str = "apartamento_residencial") -> str:
    """
    Gera a URL padrão de busca do VivaReal com base nos parâmetros.
    """
    slug_cidade = normalizar_slug_vivareal(cidade)

    return f"https://www.vivareal.com.br/{tipo_contrato}/sp/{slug_cidade}/{tipo_imovel}/"
