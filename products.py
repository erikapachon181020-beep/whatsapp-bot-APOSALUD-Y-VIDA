# products.py

DURACION_PRODUCTOS = {
    "colageno hidrolizado": 30,
    "colageno marino": 30,
    "curcuma": 25,
    "ajo": 20,
}

INFO_PRODUCTOS = {
    "colageno hidrolizado": {
        "imagen": "https://tusitio.com/img/colageno.jpg",
        "uso": "Tomar después del desayuno",
        "beneficios": "Mejora piel, cabello y uñas",
        "ingredientes": "Colágeno hidrolizado, vitamina C"
    },
    "curcuma": {
        "imagen": "https://tusitio.com/img/curcuma.jpg",
        "uso": "Tomar después de comidas",
        "beneficios": "Antiinflamatorio natural",
        "ingredientes": "Cúrcuma natural"
    },
    "ajo": {
        "imagen": "https://tusitio.com/img/ajo.jpg",
        "uso": "Tomar en ayunas",
        "beneficios": "Mejora circulación",
        "ingredientes": "Extracto de ajo"
    }
}


def get_duracion(producto: str) -> int:
    return DURACION_PRODUCTOS.get(producto.lower(), 30)


def get_info(producto: str):
    return INFO_PRODUCTOS.get(producto.lower())