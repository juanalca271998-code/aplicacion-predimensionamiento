from __future__ import annotations

from domain.unidades import area_a_unidad_mostrada
from domain.vigas_core import DatosViga, ResultadoViga, es_modo_manual, sugerir_barras


def generar_texto_comprobaciones(resultado: ResultadoViga) -> str:
    lines = [
        "=== COMPROBACIONES NORMATIVAS DE VIGA ===",
        "",
        "1. FLEXION POSITIVA",
        _ratio_linea("Mu+/φMn+", resultado.ratio_flex_pos),
        "2. FLEXION NEGATIVA IZQUIERDA",
        _ratio_linea("Mu- izq/φMn- izq", resultado.ratio_flex_neg_i),
        "3. FLEXION NEGATIVA DERECHA",
        _ratio_linea("Mu- der/φMn- der", resultado.ratio_flex_neg_d),
        "4. CORTANTE IZQUIERDO",
        _ratio_linea("Vu izq/φVn izq", resultado.ratio_v_i),
        "5. CORTANTE DERECHO",
        _ratio_linea("Vu der/φVn der", resultado.ratio_v_d),
        "6. TORSION",
        _ratio_linea("Tu/φTn", resultado.ratio_t) if resultado.ratio_t is not None else "- Sin torsion actuante.",
        "7. ACERO MINIMO A FLEXION",
        f"- Inferior: {'OK' if resultado.as_inf_cumple_min else 'NO CUMPLE'}",
        f"- Superior izquierdo: {'OK' if resultado.as_sup_i_cumple_min else 'NO CUMPLE'}",
        f"- Superior derecho: {'OK' if resultado.as_sup_d_cumple_min else 'NO CUMPLE'}",
        "8. ACERO MINIMO A CORTANTE",
        f"- Av/s minimo = {resultado.av_s_min:.4f} mm²/mm",
        f"- Av/s requerido = {resultado.av_s_req_final:.4f} mm²/mm",
        "9. SEPARACION LIBRE ENTRE BARRAS",
        resultado.sep_inf["texto"],
        resultado.sep_sup_i["texto"],
        resultado.sep_sup_d["texto"],
        "10. ALTURA MINIMA SEGUN APOYO",
        f"- Altura minima sugerida ≈ {resultado.altura_min_mm:.2f} mm {'OK' if resultado.altura_ok else 'NO CUMPLE'}",
        "11. DIAGNOSTICO DE SOBREARMADO",
        f"- Cuantia alta detectada {'OK' if resultado.cuantia_alta else 'NO'}",
        "12. DIAGNOSTICO DE SOBREDIMENSIONAMIENTO",
        f"- Mayor relacion demanda/capacidad = {max(_ratios_validos(resultado)):.3f}" if _ratios_validos(resultado) else "- No disponible",
        "",
        "=== DIAGNOSTICO FINAL ===",
        f"- {resultado.diagnostico_categoria}: {resultado.diagnostico_mensaje}",
    ]
    return "\n".join(lines)


def generar_texto_resultados(
    datos: DatosViga,
    resultado: ResultadoViga,
    unidad_area_acero: str,
    diametros_sugeridos_mm: list[float],
    unidad_longitud: str,
    diametro_estribo_texto: str,
) -> str:
    lines = [
        "=== RESUMEN INGENIERIL DE VIGA ===",
        "",
        f"Veredicto global: {'CUMPLE' if resultado.cumple_global else 'NO CUMPLE'}",
        f"Diagnostico final: {resultado.diagnostico_categoria}",
        "",
        "1. DATOS GENERALES",
        f"- Norma: {datos.norma['nombre']}",
        f"- Modo: {datos.modo}",
        f"- Tipo de apoyo: {datos.tipo_apoyo}",
        f"- Luz = {datos.luz_mm:.2f} mm",
        f"- bw = {datos.bw_mm:.2f} mm",
        f"- h = {datos.h_mm:.2f} mm",
        "",
        "2. RESISTENCIA Y DEMANDA",
        f"- φMn positivo = {resultado.phi_mn_pos_kNm:.2f} kN·m",
        f"- φMn negativo izquierdo = {resultado.phi_mn_neg_i_kNm:.2f} kN·m",
        f"- φMn negativo derecho = {resultado.phi_mn_neg_d_kNm:.2f} kN·m",
        f"- φVn izquierdo = {resultado.phi_vn_i_kN:.2f} kN",
        f"- φVn derecho = {resultado.phi_vn_d_kN:.2f} kN",
        f"- φTn = {resultado.phi_tn_kNm:.2f} kN·m" if datos.Tu_kNm > 0 else "- φTn: no aplica",
        f"- Exigencia Mu+ = {datos.Mu_pos_kNm:.2f} kN·m",
        f"- Exigencia Mu- izq = {datos.Mu_neg_i_kNm:.2f} kN·m",
        f"- Exigencia Mu- der = {datos.Mu_neg_d_kNm:.2f} kN·m",
        f"- Exigencia Vu izq = {datos.Vu_i_kN:.2f} kN",
        f"- Exigencia Vu der = {datos.Vu_d_kN:.2f} kN",
        f"- Exigencia Tu = {datos.Tu_kNm:.2f} kN·m",
        "",
        "3. ACERO Y ESTRIBOS",
        f"- As inferior = {area_a_unidad_mostrada(resultado.as_inf_mm2, unidad_area_acero):.2f} {unidad_area_acero}",
        f"- As superior izquierdo = {area_a_unidad_mostrada(resultado.as_sup_i_mm2, unidad_area_acero):.2f} {unidad_area_acero}",
        f"- As superior derecho = {area_a_unidad_mostrada(resultado.as_sup_d_mm2, unidad_area_acero):.2f} {unidad_area_acero}",
    ]

    if es_modo_manual(datos.modo):
        lines.append(
            f"- Av/s equivalente provisto = {(datos.ramas * 3.141592653589793 * datos.db_estribo_mm ** 2 / 4.0 / max(datos.s_est_mm, 1e-9)):.4f} mm²/mm"
        )
        lines.append(f"- Separacion provista de estribos = {resultado.s_sugerida_mm:.2f} mm")
    else:
        lines.append(
            f"- Sugerencia barras inferior: {sugerir_barras(resultado.as_inf_mm2, datos.bw_mm, datos.rec_mm, datos.db_estribo_mm, datos.dag_mm, diametros_sugeridos_mm)}"
        )
        lines.append(
            f"- Sugerencia barras superior izquierda: {sugerir_barras(resultado.as_sup_i_mm2, datos.bw_mm, datos.rec_mm, datos.db_estribo_mm, datos.dag_mm, diametros_sugeridos_mm)}"
        )
        lines.append(
            f"- Sugerencia barras superior derecha: {sugerir_barras(resultado.as_sup_d_mm2, datos.bw_mm, datos.rec_mm, datos.db_estribo_mm, datos.dag_mm, diametros_sugeridos_mm)}"
        )
        lines.append(f"- Av/s requerido = {resultado.av_s_req_final:.4f} mm²/mm")
        lines.append(f"- Separacion sugerida de estribos = {resultado.s_sugerida_mm:.2f} mm")
        lines.append(f"- At/s requerido = {resultado.at_s_req:.4f} mm²/mm" if datos.Tu_kNm > 0 else "- At/s requerido: no aplica")
        lines.append(
            f"- Al requerido por torsion = {area_a_unidad_mostrada(resultado.al_tor_req_mm2, unidad_area_acero):.2f} {unidad_area_acero}"
            if datos.Tu_kNm > 0 else "- Al requerido por torsion: no aplica"
        )

    lines.extend([
        "",
        "4. DIAGNOSTICO",
        f"- Estado: {'Cumple' if resultado.cumple_global else 'No cumple'}",
        f"- Diagnostico final: {resultado.diagnostico_mensaje}",
        "- Recomendaciones automaticas:",
    ])
    lines.extend(resultado.recomendaciones or ["- Sin recomendaciones adicionales."])
    return "\n".join(lines)


def generar_texto_armado(
    datos: DatosViga,
    resultado: ResultadoViga,
    unidad_area_acero: str,
    unidad_longitud: str,
    diametros_sugeridos_mm: list[float],
    db_inf_texto: str,
    db_sup_i_texto: str,
    db_sup_d_texto: str,
    db_estribo_texto: str,
    mm_a_longitud_usuario,
) -> str:
    if es_modo_manual(datos.modo):
        return (
            "ARMADO INGRESADO\n"
            f"Inferior: {datos.n_inf} Ø{db_inf_texto}\n"
            f"Superior izquierda: {datos.n_sup_i} Ø{db_sup_i_texto}\n"
            f"Superior derecha: {datos.n_sup_d} Ø{db_sup_d_texto}\n"
            f"Estribos: {datos.ramas} ramas Ø{db_estribo_texto} @ {mm_a_longitud_usuario(resultado.s_sugerida_mm):.2f} {unidad_longitud}"
        )

    return (
        "ARMADO ESTIMADO\n"
        f"Inferior: {sugerir_barras(resultado.as_inf_mm2, datos.bw_mm, datos.rec_mm, datos.db_estribo_mm, datos.dag_mm, diametros_sugeridos_mm)}\n"
        f"Superior izquierda: {sugerir_barras(resultado.as_sup_i_mm2, datos.bw_mm, datos.rec_mm, datos.db_estribo_mm, datos.dag_mm, diametros_sugeridos_mm)}\n"
        f"Superior derecha: {sugerir_barras(resultado.as_sup_d_mm2, datos.bw_mm, datos.rec_mm, datos.db_estribo_mm, datos.dag_mm, diametros_sugeridos_mm)}\n"
        f"Estribos sugeridos: {datos.ramas} ramas Ø{db_estribo_texto} @ {mm_a_longitud_usuario(resultado.s_sugerida_mm):.2f} {unidad_longitud}"
    )


def _ratio_linea(etiqueta: str, ratio: float | None) -> str:
    if ratio is None:
        return f"- {etiqueta} no disponible"
    return f"- {etiqueta} = {ratio:.3f} {'OK' if ratio <= 1.0 else 'NO CUMPLE'}"


def _ratios_validos(resultado: ResultadoViga) -> list[float]:
    return [
        ratio for ratio in [
            resultado.ratio_flex_pos,
            resultado.ratio_flex_neg_i,
            resultado.ratio_flex_neg_d,
            resultado.ratio_v_i,
            resultado.ratio_v_d,
            resultado.ratio_t,
        ]
        if ratio is not None
    ]
