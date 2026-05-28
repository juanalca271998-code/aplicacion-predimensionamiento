resultados = {
    "columnas": {},
    "vigas": {},
    "zapatas": {},
    "sismo": {},
    "viento": {}
}

configuracion = {
    "unidad_fuerza": "kN",
    "unidad_momento": "kN·m",
    "unidad_longitud": "mm",
    "unidad_recubrimiento": "mm",
    "unidad_diametro_barra": "mm",
    "unidad_area_acero": "mm²"
}


def guardar_resultado(modulo, data):
    resultados[modulo] = data


def obtener_resultados():
    return resultados


def guardar_configuracion(clave, valor):
    configuracion[clave] = valor


def obtener_configuracion():
    return configuracion
