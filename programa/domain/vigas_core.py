from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class DatosViga:
    modo: str
    norma: dict
    tipo_apoyo: str
    luz_mm: float
    bw_mm: float
    h_mm: float
    rec_mm: float
    db_estribo_mm: float
    dag_mm: float
    fc: float
    fy: float
    fyt: float
    wu_kN_m: float
    P_kN: float
    x_p_mm: float
    Mu_pos_kNm: float
    Mu_neg_i_kNm: float
    Mu_neg_d_kNm: float
    Vu_i_kN: float
    Vu_d_kN: float
    Tu_kNm: float
    Pu_kN: float
    n_inf: int
    n_sup_i: int
    n_sup_d: int
    db_inf_mm: float
    db_sup_i_mm: float
    db_sup_d_mm: float
    ramas: int
    s_est_mm: float

    def __getitem__(self, key: str):
        return getattr(self, key)


@dataclass
class ResultadoViga:
    cumple_global: bool
    diagnostico_categoria: str
    diagnostico_mensaje: str
    as_inf_mm2: float
    as_sup_i_mm2: float
    as_sup_d_mm2: float
    phi_mn_pos_kNm: float
    phi_mn_neg_i_kNm: float
    phi_mn_neg_d_kNm: float
    phi_vn_i_kN: float
    phi_vn_d_kN: float
    phi_tn_kNm: float
    ratio_flex_pos: float | None
    ratio_flex_neg_i: float | None
    ratio_flex_neg_d: float | None
    ratio_v_i: float | None
    ratio_v_d: float | None
    ratio_t: float | None
    s_sugerida_mm: float
    av_s_req_final: float
    av_s_min: float
    at_s_req: float
    al_tor_req_mm2: float
    recomendaciones: list[str]
    comprobaciones: list[str]
    as_min_inf_mm2: float = 0.0
    as_min_sup_i_mm2: float = 0.0
    as_min_sup_d_mm2: float = 0.0
    d_inf_mm: float = 0.0
    d_sup_i_mm: float = 0.0
    d_sup_d_mm: float = 0.0
    cuantia_inf: float = 0.0
    cuantia_sup_i: float = 0.0
    cuantia_sup_d: float = 0.0
    cuantia_alta: bool = False
    separaciones_ok: bool = True
    altura_ok: bool = True
    altura_min_mm: float = 0.0
    x_p_ajustada_mm: float = 0.0
    as_inf_cumple_min: bool = True
    as_sup_i_cumple_min: bool = True
    as_sup_d_cumple_min: bool = True
    sep_inf: dict = field(default_factory=dict)
    sep_sup_i: dict = field(default_factory=dict)
    sep_sup_d: dict = field(default_factory=dict)
    vc_i_kN: float = 0.0
    vc_d_kN: float = 0.0
    vs_i_kN: float = 0.0
    vs_d_kN: float = 0.0


def es_modo_manual(modo: str) -> bool:
    return modo == "Verificar capacidad con acero ingresado"


def bar_area_mm2(d_mm: float) -> float:
    return math.pi * d_mm ** 2 / 4.0


def profundidad_efectiva(h_mm: float, rec_mm: float, db_estribo_mm: float, db_barra_mm: float) -> float:
    return h_mm - rec_mm - db_estribo_mm - db_barra_mm / 2.0


def rho_min_flexion(fc: float, fy: float) -> float:
    return max(0.25 * math.sqrt(fc) / fy, 1.4 / fy)


def as_min_flexion(bw_mm: float, d_mm: float, fc: float, fy: float) -> float:
    return rho_min_flexion(fc, fy) * bw_mm * d_mm


def resolver_as_flexion(mu_kNm: float, bw_mm: float, d_mm: float, fc: float, fy: float, phi_flex: float) -> float:
    mu_nmm = max(mu_kNm, 0.0) * 1e6
    mn_requerido = mu_nmm / max(phi_flex, 1e-9)
    if mn_requerido <= 0:
        return 0.0

    low = 0.0
    high = bw_mm * d_mm * 0.08
    for _ in range(120):
        mid = 0.5 * (low + high)
        a = mid * fy / max(0.85 * fc * bw_mm, 1e-9)
        mn_mid = mid * fy * max(d_mm - a / 2.0, 0.0)
        if mn_mid >= mn_requerido:
            high = mid
        else:
            low = mid
    return high


def capacidad_flexion(as_mm2: float, bw_mm: float, d_mm: float, fc: float, fy: float, phi_flex: float) -> float:
    if as_mm2 <= 0 or d_mm <= 0:
        return 0.0
    a = as_mm2 * fy / max(0.85 * fc * bw_mm, 1e-9)
    mn = as_mm2 * fy * max(d_mm - a / 2.0, 0.0)
    return phi_flex * mn / 1e6


def vc_kN(fc: float, bw_mm: float, d_mm: float, pu_kN: float = 0.0) -> float:
    ag = bw_mm * max(d_mm, 1.0)
    pu_term = min((pu_kN * 1000.0) / max(6.0 * ag, 1e-9), 0.3 * math.sqrt(fc)) if pu_kN > 0 else 0.0
    return (0.17 * math.sqrt(fc) + pu_term) * bw_mm * d_mm / 1000.0


def acero_requerido_cortante(vu_kN: float, fc: float, bw_mm: float, d_mm: float, fyt: float, phi_shear: float, pu_kN: float = 0.0) -> tuple[float, float]:
    vc = vc_kN(fc, bw_mm, d_mm, pu_kN)
    vs_req = max(vu_kN / max(phi_shear, 1e-9) - vc, 0.0)
    return vs_req * 1000.0 / max(fyt * d_mm, 1e-9), vc


def av_s_minimo(bw_mm: float, fyt: float, fc: float) -> float:
    # TODO: Verificar formula exacta de Av/s minimo segun ACI 318-19 / NB 1225001.
    return 0.062 * math.sqrt(max(fc, 1.0)) * bw_mm / max(fyt, 1e-9)


def separacion_sugerida_estribos(av_s_req: float, ramas: int, db_estribo_mm: float, d_mm: float) -> float:
    av = max(ramas, 2) * bar_area_mm2(db_estribo_mm)
    if av_s_req <= 1e-9:
        return min(0.75 * d_mm, 600.0)
    return min(av / av_s_req, d_mm / 2.0, 600.0)


def capacidad_cortante(fc: float, bw_mm: float, d_mm: float, fyt: float, ramas: int, db_estribo_mm: float, s_mm: float, phi_shear: float, pu_kN: float = 0.0) -> tuple[float, float, float]:
    vc = vc_kN(fc, bw_mm, d_mm, pu_kN)
    av = max(ramas, 2) * bar_area_mm2(db_estribo_mm)
    vs = av * fyt * d_mm / max(s_mm, 1e-9) / 1000.0
    return phi_shear * (vc + vs), vc, vs


def acero_requerido_torsion(tu_kNm: float, bw_mm: float, h_mm: float, rec_mm: float, db_estribo_mm: float, fyt: float, phi_torsion: float) -> tuple[float, float]:
    if tu_kNm <= 0:
        return 0.0, 0.0
    ao = max((bw_mm - 2.0 * (rec_mm + db_estribo_mm / 2.0)) * (h_mm - 2.0 * (rec_mm + db_estribo_mm / 2.0)), 1.0)
    tu_nmm = tu_kNm * 1e6
    at_s = tu_nmm / max(2.0 * phi_torsion * ao * fyt, 1e-9)
    al = at_s * (bw_mm + h_mm) / 2.0
    return at_s, al


def capacidad_torsion(bw_mm: float, h_mm: float, rec_mm: float, db_estribo_mm: float, fyt: float, ramas: int, s_mm: float, phi_torsion: float) -> float:
    ao = max((bw_mm - 2.0 * (rec_mm + db_estribo_mm / 2.0)) * (h_mm - 2.0 * (rec_mm + db_estribo_mm / 2.0)), 1.0)
    at = max(ramas, 2) * bar_area_mm2(db_estribo_mm) / 2.0
    tn = 2.0 * ao * at * fyt / max(s_mm, 1e-9)
    return phi_torsion * tn / 1e6


def check_separacion_cype(bw_mm: float, rec_mm: float, db_estribo_mm: float, dag_mm: float, n_barras: int, db_barra_mm: float, zona: str) -> dict:
    if n_barras <= 1 or db_barra_mm <= 0:
        return {
            "cumple": True,
            "texto": f"- {zona}: sin conflicto de separacion libre.",
            "s_libre_mm": None,
            "sl_min_mm": None,
        }

    s1 = db_barra_mm
    s2 = 25.0
    s3 = (4.0 / 3.0) * dag_mm
    sl_min = max(s1, s2, s3)
    b_int = bw_mm - 2.0 * (rec_mm + db_estribo_mm)
    s_libre = (b_int - n_barras * db_barra_mm) / max(n_barras - 1, 1)
    cumple = s_libre >= sl_min
    return {
        "cumple": cumple,
        "texto": f"- {zona}: s_libre = {s_libre:.2f} mm ; sl,min = {sl_min:.2f} mm {'OK' if cumple else 'NO CUMPLE'}",
        "s_libre_mm": s_libre,
        "sl_min_mm": sl_min,
    }


def apoyo_factor_altura(tipo_apoyo: str) -> float:
    if tipo_apoyo == "Voladizo":
        return 8.0
    if tipo_apoyo == "Simplemente apoyada":
        return 16.0
    if tipo_apoyo == "Un extremo continuo":
        return 18.5
    return 21.0


def check_altura_minima(luz_mm: float, h_mm: float, tipo_apoyo: str) -> dict:
    factor = apoyo_factor_altura(tipo_apoyo)
    h_min = luz_mm / factor if factor > 0 else 0.0
    cumple = h_mm >= h_min
    return {
        "cumple": cumple,
        "h_min_mm": h_min,
        "texto": f"- Altura minima sugerida ≈ {h_min:.2f} mm {'OK' if cumple else 'NO CUMPLE'}",
    }


def sugerir_barras(as_req_mm2: float, bw_mm: float | None, rec_mm: float | None, db_estribo_mm: float | None, dag_mm: float | None, diametros_mm: list[float]) -> str:
    if as_req_mm2 <= 0:
        return "No se requiere acero adicional."

    candidatos: list[tuple[float, int, float]] = []
    for db_mm in diametros_mm:
        area = bar_area_mm2(db_mm)
        for n_barras in range(2, 25):
            as_prov = n_barras * area
            if as_prov < as_req_mm2:
                continue
            if None not in (bw_mm, rec_mm, db_estribo_mm, dag_mm):
                check = check_separacion_cype(bw_mm, rec_mm, db_estribo_mm, dag_mm, n_barras, db_mm, "Sugerencia")
                if not check["cumple"]:
                    continue
            candidatos.append((as_prov, n_barras, db_mm))

    if not candidatos:
        return "No se encontro una sugerencia simple en una sola hilera. Conviene aumentar seccion o revisar el detallado."

    candidatos.sort(key=lambda item: (item[0], item[1], item[2]))
    mejor = candidatos[0]
    return f"{mejor[1]} barras Ø{int(round(mejor[2]))} mm"


def diagnostico_final(ratios: list[float], cuantias_altas: bool, separaciones_ok: bool, altura_ok: bool) -> tuple[str, str]:
    ratio_control = max(ratios) if ratios else None
    if not separaciones_ok:
        return "Detallado no conforme", "Detallado no conforme: revisar separacion libre y disposicion de barras."
    if cuantias_altas:
        return "Posible sobrearmado", "Posible sobrearmado: revisar cantidad, diametro o distribucion de barras."
    if ratio_control is None:
        return "Diagnostico no disponible", "Diagnostico no disponible: revisar datos y resultados."
    if ratio_control > 1.00:
        return "No cumple", "No cumple: aumentar seccion, acero o revisar esfuerzos."
    if ratio_control >= 0.85:
        return "Cumple ajustado", "Cumple ajustado: verificar con CYPE antes de optimizar."
    if ratio_control >= 0.55:
        return "Cumple adecuadamente", "Cumple adecuadamente: seccion razonable."
    if ratio_control < 0.50 and not altura_ok:
        return "Cumple adecuadamente", "Cumple adecuadamente: la demanda es baja, pero la altura minima aun gobierna."
    if ratio_control < 0.50 and altura_ok:
        return "Posible sobredimensionamiento", "Posible sobredimensionamiento: probar una seccion menor en CYPE."
    return "Cumple adecuadamente", "Cumple adecuadamente: seccion razonable."


def validar_datos_viga(datos: DatosViga) -> None:
    if datos.bw_mm <= 0:
        raise ValueError("bw debe ser mayor que cero.")
    if datos.h_mm <= 0:
        raise ValueError("h debe ser mayor que cero.")
    if datos.luz_mm <= 0:
        raise ValueError("La luz debe ser mayor que cero.")
    if datos.rec_mm < 0:
        raise ValueError("El recubrimiento no puede ser negativo.")
    if datos.rec_mm >= min(datos.bw_mm, datos.h_mm) / 2.0:
        raise ValueError("El recubrimiento es demasiado grande para la seccion.")
    if datos.fc <= 0 or datos.fy <= 0 or datos.fyt <= 0:
        raise ValueError("f'c, fy y fyt deben ser mayores que cero.")
    if es_modo_manual(datos.modo) and datos.s_est_mm <= 0:
        raise ValueError("La separacion de estribos debe ser mayor que cero en modo manual.")


def calcular_viga(datos: DatosViga) -> ResultadoViga:
    validar_datos_viga(datos)

    phi_flex = datos.norma["phi_flex"]
    phi_shear = datos.norma["phi_shear"]
    phi_torsion = datos.norma["phi_torsion"]

    recomendaciones: list[str] = []
    x_p_ajustada = min(max(datos.x_p_mm, 0.0), datos.luz_mm)
    if abs(x_p_ajustada - datos.x_p_mm) > 1e-9:
        recomendaciones.append("- La posicion de la carga puntual fue ajustada al rango de la luz.")

    d_inf = profundidad_efectiva(datos.h_mm, datos.rec_mm, datos.db_estribo_mm, datos.db_inf_mm)
    d_sup_i = profundidad_efectiva(datos.h_mm, datos.rec_mm, datos.db_estribo_mm, datos.db_sup_i_mm)
    d_sup_d = profundidad_efectiva(datos.h_mm, datos.rec_mm, datos.db_estribo_mm, datos.db_sup_d_mm)
    if min(d_inf, d_sup_i, d_sup_d) <= 0:
        raise ValueError("La profundidad efectiva resulto invalida. Revisa geometria, recubrimiento y diametros.")

    as_min_inf = as_min_flexion(datos.bw_mm, d_inf, datos.fc, datos.fy)
    as_min_sup_i = as_min_flexion(datos.bw_mm, d_sup_i, datos.fc, datos.fy)
    as_min_sup_d = as_min_flexion(datos.bw_mm, d_sup_d, datos.fc, datos.fy)

    if es_modo_manual(datos.modo):
        as_inf = datos.n_inf * bar_area_mm2(datos.db_inf_mm)
        as_sup_i = datos.n_sup_i * bar_area_mm2(datos.db_sup_i_mm)
        as_sup_d = datos.n_sup_d * bar_area_mm2(datos.db_sup_d_mm)
    else:
        as_inf = max(resolver_as_flexion(datos.Mu_pos_kNm, datos.bw_mm, d_inf, datos.fc, datos.fy, phi_flex), as_min_inf)
        as_sup_i = max(resolver_as_flexion(datos.Mu_neg_i_kNm, datos.bw_mm, d_sup_i, datos.fc, datos.fy, phi_flex), as_min_sup_i)
        as_sup_d = max(resolver_as_flexion(datos.Mu_neg_d_kNm, datos.bw_mm, d_sup_d, datos.fc, datos.fy, phi_flex), as_min_sup_d)

    phi_mn_pos = capacidad_flexion(as_inf, datos.bw_mm, d_inf, datos.fc, datos.fy, phi_flex)
    phi_mn_neg_i = capacidad_flexion(as_sup_i, datos.bw_mm, d_sup_i, datos.fc, datos.fy, phi_flex)
    phi_mn_neg_d = capacidad_flexion(as_sup_d, datos.bw_mm, d_sup_d, datos.fc, datos.fy, phi_flex)

    av_s_req_i, vc_i = acero_requerido_cortante(datos.Vu_i_kN, datos.fc, datos.bw_mm, d_inf, datos.fyt, phi_shear, datos.Pu_kN)
    av_s_req_d, vc_d = acero_requerido_cortante(datos.Vu_d_kN, datos.fc, datos.bw_mm, d_inf, datos.fyt, phi_shear, datos.Pu_kN)
    av_s_req = max(av_s_req_i, av_s_req_d)
    av_s_min = av_s_minimo(datos.bw_mm, datos.fyt, datos.fc)
    av_s_req_final = max(av_s_req, av_s_min if max(datos.Vu_i_kN, datos.Vu_d_kN) > 0 else 0.0)

    if es_modo_manual(datos.modo):
        s_sugerida = datos.s_est_mm
        phi_vn_i, _, vs_i = capacidad_cortante(datos.fc, datos.bw_mm, d_inf, datos.fyt, datos.ramas, datos.db_estribo_mm, datos.s_est_mm, phi_shear, datos.Pu_kN)
        phi_vn_d, _, vs_d = capacidad_cortante(datos.fc, datos.bw_mm, d_inf, datos.fyt, datos.ramas, datos.db_estribo_mm, datos.s_est_mm, phi_shear, datos.Pu_kN)
    else:
        s_sugerida = separacion_sugerida_estribos(av_s_req_final, datos.ramas, datos.db_estribo_mm, d_inf)
        phi_vn_i, _, vs_i = capacidad_cortante(datos.fc, datos.bw_mm, d_inf, datos.fyt, datos.ramas, datos.db_estribo_mm, s_sugerida, phi_shear, datos.Pu_kN)
        phi_vn_d, _, vs_d = capacidad_cortante(datos.fc, datos.bw_mm, d_inf, datos.fyt, datos.ramas, datos.db_estribo_mm, s_sugerida, phi_shear, datos.Pu_kN)

    at_s_req, al_tor_req = acero_requerido_torsion(datos.Tu_kNm, datos.bw_mm, datos.h_mm, datos.rec_mm, datos.db_estribo_mm, datos.fyt, phi_torsion)
    phi_tn = capacidad_torsion(
        datos.bw_mm,
        datos.h_mm,
        datos.rec_mm,
        datos.db_estribo_mm,
        datos.fyt,
        datos.ramas,
        datos.s_est_mm if es_modo_manual(datos.modo) else max(s_sugerida, 1.0),
        phi_torsion,
    ) if datos.Tu_kNm > 0 else 0.0

    sep_inf = check_separacion_cype(datos.bw_mm, datos.rec_mm, datos.db_estribo_mm, datos.dag_mm, datos.n_inf, datos.db_inf_mm, "Acero inferior")
    sep_sup_i = check_separacion_cype(datos.bw_mm, datos.rec_mm, datos.db_estribo_mm, datos.dag_mm, datos.n_sup_i, datos.db_sup_i_mm, "Acero superior izquierdo")
    sep_sup_d = check_separacion_cype(datos.bw_mm, datos.rec_mm, datos.db_estribo_mm, datos.dag_mm, datos.n_sup_d, datos.db_sup_d_mm, "Acero superior derecho")
    altura_min = check_altura_minima(datos.luz_mm, datos.h_mm, datos.tipo_apoyo)

    as_inf_cumple_min = as_inf >= as_min_inf
    as_sup_i_cumple_min = as_sup_i >= as_min_sup_i
    as_sup_d_cumple_min = as_sup_d >= as_min_sup_d

    ratio_flex_pos = datos.Mu_pos_kNm / phi_mn_pos if phi_mn_pos > 0 else None
    ratio_flex_neg_i = datos.Mu_neg_i_kNm / phi_mn_neg_i if phi_mn_neg_i > 0 else None
    ratio_flex_neg_d = datos.Mu_neg_d_kNm / phi_mn_neg_d if phi_mn_neg_d > 0 else None
    ratio_v_i = datos.Vu_i_kN / phi_vn_i if phi_vn_i > 0 else None
    ratio_v_d = datos.Vu_d_kN / phi_vn_d if phi_vn_d > 0 else None
    ratio_t = datos.Tu_kNm / phi_tn if phi_tn > 0 and datos.Tu_kNm > 0 else None

    cuantia_inf = as_inf / max(datos.bw_mm * d_inf, 1e-9)
    cuantia_sup_i = as_sup_i / max(datos.bw_mm * d_sup_i, 1e-9)
    cuantia_sup_d = as_sup_d / max(datos.bw_mm * d_sup_d, 1e-9)
    cuantia_alta = max(cuantia_inf, cuantia_sup_i, cuantia_sup_d) >= 0.035

    ratios = [ratio for ratio in [ratio_flex_pos, ratio_flex_neg_i, ratio_flex_neg_d, ratio_v_i, ratio_v_d, ratio_t] if ratio is not None]
    separaciones_ok = sep_inf["cumple"] and sep_sup_i["cumple"] and sep_sup_d["cumple"]
    diagnostico_categoria, diagnostico_mensaje = diagnostico_final(ratios, cuantia_alta, separaciones_ok, altura_min["cumple"])

    cumple_global = (
        (ratio_flex_pos is None or ratio_flex_pos <= 1.0)
        and (ratio_flex_neg_i is None or ratio_flex_neg_i <= 1.0)
        and (ratio_flex_neg_d is None or ratio_flex_neg_d <= 1.0)
        and (ratio_v_i is None or ratio_v_i <= 1.0)
        and (ratio_v_d is None or ratio_v_d <= 1.0)
        and (ratio_t is None or ratio_t <= 1.0)
        and separaciones_ok
        and altura_min["cumple"]
        and as_inf_cumple_min
        and as_sup_i_cumple_min
        and as_sup_d_cumple_min
    )

    if not cumple_global:
        if ratio_flex_pos is not None and ratio_flex_pos > 1.0:
            recomendaciones.append("- Aumentar acero inferior o peralte para flexion positiva.")
        if ratio_flex_neg_i is not None and ratio_flex_neg_i > 1.0:
            recomendaciones.append("- Aumentar acero superior izquierdo para momento negativo.")
        if ratio_flex_neg_d is not None and ratio_flex_neg_d > 1.0:
            recomendaciones.append("- Aumentar acero superior derecho para momento negativo.")
        if (ratio_v_i is not None and ratio_v_i > 1.0) or (ratio_v_d is not None and ratio_v_d > 1.0):
            recomendaciones.append("- Reducir separacion de estribos o aumentar ramas/diametro.")
        if ratio_t is not None and ratio_t > 1.0:
            recomendaciones.append("- Revisar refuerzo por torsion: At/s y acero longitudinal adicional.")
        if not separaciones_ok:
            recomendaciones.append("- Ajustar cantidad o diametro de barras para cumplir separacion libre minima.")
        if not altura_min["cumple"]:
            recomendaciones.append("- Aumentar h o revisar el esquema resistente.")
    else:
        if diagnostico_categoria == "Cumple ajustado":
            recomendaciones.append("- Revisar el caso en CYPE antes de optimizar.")
        elif diagnostico_categoria == "Posible sobredimensionamiento":
            recomendaciones.append("- Probar una seccion menor o una distribucion de acero mas eficiente en CYPE.")
        elif diagnostico_categoria == "Posible sobrearmado":
            recomendaciones.append("- Reducir cantidad de barras o redistribuir diametros manteniendo capacidad.")
        else:
            recomendaciones.append("- La viga presenta un rango preliminar razonable.")

    comprobaciones = [
        "1. Flexion positiva",
        "2. Flexion negativa izquierda",
        "3. Flexion negativa derecha",
        "4. Cortante izquierdo",
        "5. Cortante derecho",
        "6. Torsion" if datos.Tu_kNm > 0 else "6. Sin torsion actuante",
        "7. Acero minimo a flexion",
        "8. Acero minimo a cortante",
        "9. Separacion libre entre barras",
        "10. Altura minima segun apoyo",
        "11. Diagnostico de sobrearmado",
        "12. Diagnostico de sobredimensionamiento",
    ]

    return ResultadoViga(
        cumple_global=cumple_global,
        diagnostico_categoria=diagnostico_categoria,
        diagnostico_mensaje=diagnostico_mensaje,
        as_inf_mm2=as_inf,
        as_sup_i_mm2=as_sup_i,
        as_sup_d_mm2=as_sup_d,
        phi_mn_pos_kNm=phi_mn_pos,
        phi_mn_neg_i_kNm=phi_mn_neg_i,
        phi_mn_neg_d_kNm=phi_mn_neg_d,
        phi_vn_i_kN=phi_vn_i,
        phi_vn_d_kN=phi_vn_d,
        phi_tn_kNm=phi_tn,
        ratio_flex_pos=ratio_flex_pos,
        ratio_flex_neg_i=ratio_flex_neg_i,
        ratio_flex_neg_d=ratio_flex_neg_d,
        ratio_v_i=ratio_v_i,
        ratio_v_d=ratio_v_d,
        ratio_t=ratio_t,
        s_sugerida_mm=s_sugerida,
        av_s_req_final=av_s_req_final,
        av_s_min=av_s_min,
        at_s_req=at_s_req,
        al_tor_req_mm2=al_tor_req,
        recomendaciones=recomendaciones,
        comprobaciones=comprobaciones,
        as_min_inf_mm2=as_min_inf,
        as_min_sup_i_mm2=as_min_sup_i,
        as_min_sup_d_mm2=as_min_sup_d,
        d_inf_mm=d_inf,
        d_sup_i_mm=d_sup_i,
        d_sup_d_mm=d_sup_d,
        cuantia_inf=cuantia_inf,
        cuantia_sup_i=cuantia_sup_i,
        cuantia_sup_d=cuantia_sup_d,
        cuantia_alta=cuantia_alta,
        separaciones_ok=separaciones_ok,
        altura_ok=altura_min["cumple"],
        altura_min_mm=altura_min["h_min_mm"],
        x_p_ajustada_mm=x_p_ajustada,
        as_inf_cumple_min=as_inf_cumple_min,
        as_sup_i_cumple_min=as_sup_i_cumple_min,
        as_sup_d_cumple_min=as_sup_d_cumple_min,
        sep_inf=sep_inf,
        sep_sup_i=sep_sup_i,
        sep_sup_d=sep_sup_d,
        vc_i_kN=vc_i,
        vc_d_kN=vc_d,
        vs_i_kN=vs_i,
        vs_d_kN=vs_d,
    )
