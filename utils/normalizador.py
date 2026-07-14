import re
import unicodedata

MAPEAMENTO_CAMPOS = {
    "area": [
        "área",
        "área útil",
        "área total",
        "tamanho",
        "m²",
        "metros quadrados",
        "área terreno",
        "dimensão"
    ],

    "preco_total": [
        "preço",
        "valor",
        "preço total",
        "valor total",
        "venda",
        "valor de venda"
    ],

    "localizacao": [
        "localização",
        "endereço",
        "bairro",
        "logradouro",
        "zona",
        "rua",
        "avenida",
        "alameda",
        "travessa",
        "condomínio",
        "loteamento"
    ],

    "tipo_imovel": [
        "terreno",
        "lote",
        "loteamento",
        "área",
        "gleba",
        "chácara",
        "sitio",
        "sítio",
        "fazenda"
    ]
}


def limpar_texto(texto):
    if not texto:
        return ""

    texto = re.sub(r"\s+", " ", str(texto).strip().lower())

    texto = "".join(
        c
        for c in unicodedata.normalize("NFKD", texto)
        if not unicodedata.combining(c)
    )

    return texto


def mapear_campo_sistema(texto_html):

    if not texto_html:
        return None

    texto = limpar_texto(texto_html)

    for campo, aliases in MAPEAMENTO_CAMPOS.items():

        for alias in aliases:

            if alias in texto:
                return campo

    return None


def tratar_valor_numerico(campo, valor_texto):

    if not valor_texto:
        return None

    texto_limpo = re.sub(r"[^\d,.]", "", str(valor_texto))

    if not texto_limpo:
        return None

    try:

        if "," in texto_limpo:
            texto_limpo = (
                texto_limpo
                .replace(".", "")
                .replace(",", ".")
            )

        return float(texto_limpo)

    except ValueError:
        return None
