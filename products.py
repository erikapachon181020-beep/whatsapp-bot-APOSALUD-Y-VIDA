# products.py — Duracion e info de productos APOSALUD Y VIDA

DURACION_PRODUCTOS = {
    "ajo":                      20,
    "citrato":                  30,
    "colageno hidrolizado":     30,
    "colageno marino":          30,
    "complejo b":               30,
    "curcuma":                  30,
    "gomas de colageno":        30,
    "gomas de resveratrol":     30,
    "gomas de vinagre":         30,
    "grainlax":                 25,
    "hit 10":                   30,
    "kolag":                    30,
    "koncal":                   30,
    "nad+resveratrol":          30,
    "omega 3":                  30,
    "omega 3,6,9":              30,
    "oregano":                  30,
}

INFO_PRODUCTOS = {
    "colageno hidrolizado": {
        "uso": "Tomar en ayunas o antes de dormir",
        "beneficios": "Mejora piel, cabello, unas y articulaciones"
    },
    "colageno marino": {
        "uso": "Tomar en ayunas o antes de dormir",
        "beneficios": "Mejora piel, cabello, unas y articulaciones"
    },
    "curcuma": {
        "uso": "Tomar despues de comidas",
        "beneficios": "Antiinflamatorio natural, apoya digestion"
    },
    "ajo": {
        "uso": "Tomar en ayunas",
        "beneficios": "Mejora circulacion y sistema inmune"
    },
    "omega 3": {
        "uso": "Tomar con una comida",
        "beneficios": "Salud cardiovascular y cerebral"
    },
    "omega 3,6,9": {
        "uso": "Tomar con una comida",
        "beneficios": "Salud cardiovascular y cerebral"
    },
    "gomas de colageno": {
        "uso": "2 gomas al dia",
        "beneficios": "Mejora piel, cabello y unas de forma deliciosa"
    },
    "gomas de vinagre": {
        "uso": "2 gomas antes de comer",
        "beneficios": "Apoya digestion y metabolismo"
    },
    "complejo b": {
        "uso": "1 softgel al dia con desayuno",
        "beneficios": "Energia, sistema nervioso y metabolismo"
    },
}


def get_duracion(producto: str) -> int:
    return DURACION_PRODUCTOS.get(producto.lower().strip(), 30)


def get_info(producto: str):
    return INFO_PRODUCTOS.get(producto.lower().strip())
