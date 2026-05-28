from __future__ import annotations


def longitud_a_mm(valor: float, unidad_longitud: str) -> float:
    if unidad_longitud == "mm":
        return valor
    if unidad_longitud == "cm":
        return valor * 10.0
    if unidad_longitud == "m":
        return valor * 1000.0
    return valor


def mm_a_longitud_usuario(valor_mm: float, unidad_longitud: str) -> float:
    if unidad_longitud == "mm":
        return valor_mm
    if unidad_longitud == "cm":
        return valor_mm / 10.0
    if unidad_longitud == "m":
        return valor_mm / 1000.0
    return valor_mm


def recubrimiento_a_mm(valor: float, unidad_recubrimiento: str) -> float:
    if unidad_recubrimiento == "mm":
        return valor
    if unidad_recubrimiento == "cm":
        return valor * 10.0
    return valor


def diametro_a_mm(valor: float, unidad_diametro_barra: str) -> float:
    if unidad_diametro_barra == "mm":
        return valor
    if unidad_diametro_barra == "cm":
        return valor * 10.0
    return valor


def mm_a_diametro_usuario(valor_mm: float, unidad_diametro_barra: str) -> float:
    if unidad_diametro_barra == "mm":
        return valor_mm
    if unidad_diametro_barra == "cm":
        return valor_mm / 10.0
    return valor_mm


def fuerza_a_kN(valor: float, unidad_fuerza: str) -> float:
    if unidad_fuerza == "kN":
        return valor
    if unidad_fuerza == "tf":
        return valor * 9.80665
    if unidad_fuerza == "kgf":
        return valor * 0.00980665
    return valor


def momento_a_kNm(valor: float, unidad_momento: str) -> float:
    if unidad_momento == "kN·m":
        return valor
    if unidad_momento == "tf·m":
        return valor * 9.80665
    if unidad_momento == "kgf·m":
        return valor * 0.00980665
    return valor


def carga_distribuida_a_kN_m(valor: float, unidad_fuerza: str) -> float:
    return fuerza_a_kN(valor, unidad_fuerza)


def area_a_unidad_mostrada(area_mm2: float, unidad_area_acero: str) -> float:
    if unidad_area_acero == "mm²":
        return area_mm2
    if unidad_area_acero == "cm²":
        return area_mm2 / 100.0
    return area_mm2
