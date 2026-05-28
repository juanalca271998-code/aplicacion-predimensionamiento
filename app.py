from __future__ import annotations

from datetime import datetime
from io import BytesIO

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


FA_X = [0.067, 0.133, 0.200, 0.267, 0.333, 0.400]
FA_TABLE = {
    "S0": [0.8, 0.8, 0.8, 0.8, 0.8, 0.8],
    "S1": [0.9, 0.9, 0.9, 0.9, 0.9, 0.9],
    "S2": [1.3, 1.3, 1.2, 1.1, 1.1, 1.1],
    "S3": [1.6, 1.4, 1.2, 1.1, 1.1, 1.1],
    "S4": [2.4, 1.7, 1.3, 1.2, 1.2, 1.2],
}

FV_X = [0.053, 0.107, 0.160, 0.213, 0.267, 0.320]
FV_TABLE = {
    "S0": [0.64, 0.7, 0.8, 0.8, 0.8, 0.8],
    "S1": [0.64, 0.7, 0.8, 0.8, 0.8, 0.8],
    "S2": [1.2, 1.3, 1.5, 1.5, 1.5, 1.4],
    "S3": [2.0, 2.0, 2.0, 1.9, 1.8, 1.7],
    "S4": [3.5, 3.0, 2.8, 2.4, 2.4, 2.4],
}

STRUCTURE_TYPES = {
    "Tipo IV - Estructuras esenciales": {"ie": 1.5, "code": "IV"},
    "Tipo III - Estructuras con aglomeracion": {"ie": 1.3, "code": "III"},
    "Tipo II - Edificaciones comunes": {"ie": 1.0, "code": "II"},
    "Tipo I - Construcciones aisladas o provisorias": {"ie": None, "code": "I"},
}

STRUCTURAL_SYSTEMS = {
    "Porticos especiales de hormigon armado": {"R": 8.0, "Cd": 5.5, "deriva_max": 0.012},
    "Porticos intermedios de hormigon armado": {"R": 5.0, "Cd": 4.5, "deriva_max": 0.011},
    "Porticos ordinarios de hormigon armado": {"R": 3.0, "Cd": 2.5, "deriva_max": 0.010},
    "Muros estructurales especiales de hormigon armado": {"R": 6.0, "Cd": 5.0, "deriva_max": 0.009},
    "Muros estructurales ordinarios de hormigon armado": {"R": 5.0, "Cd": 4.5, "deriva_max": 0.008},
    "Sistema dual: porticos especiales + muros especiales": {"R": 7.0, "Cd": 5.5, "deriva_max": 0.010},
    "Albanileria armada o confinada": {"R": 3.0, "Cd": 2.5, "deriva_max": 0.004},
    "Madera por esfuerzos admisibles": {"R": 5.0, "Cd": 4.5, "deriva_max": 0.007},
    "Manual": {"R": None, "Cd": None, "deriva_max": None},
}

CDS_ORDER = {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 6}


def interpolate_table_value(x, x_values, y_values):
    if x <= x_values[0]:
        return y_values[0]

    if x >= x_values[-1]:
        return y_values[-1]

    for i in range(len(x_values) - 1):
        x1 = x_values[i]
        x2 = x_values[i + 1]
        y1 = y_values[i]
        y2 = y_values[i + 1]

        if x1 <= x <= x2:
            return y1 + (y2 - y1) * (x - x1) / (x2 - x1)

    return y_values[-1]


def get_interpolation_detail(x, x_values, y_values):
    for idx, x_value in enumerate(x_values):
        if abs(x - x_value) < 1e-12:
            return {
                "mode": "exact",
                "x": float(x),
                "x1": float(x_value),
                "x2": float(x_value),
                "y1": float(y_values[idx]),
                "y2": float(y_values[idx]),
                "result": float(y_values[idx]),
            }

    if x <= x_values[0]:
        return {
            "mode": "lower_bound",
            "x": float(x),
            "x1": float(x_values[0]),
            "x2": float(x_values[0]),
            "y1": float(y_values[0]),
            "y2": float(y_values[0]),
            "result": float(y_values[0]),
        }

    if x >= x_values[-1]:
        return {
            "mode": "upper_bound",
            "x": float(x),
            "x1": float(x_values[-1]),
            "x2": float(x_values[-1]),
            "y1": float(y_values[-1]),
            "y2": float(y_values[-1]),
            "result": float(y_values[-1]),
        }

    for i in range(len(x_values) - 1):
        x1 = x_values[i]
        x2 = x_values[i + 1]
        y1 = y_values[i]
        y2 = y_values[i + 1]
        if x1 <= x <= x2:
            result = y1 + (y2 - y1) * (x - x1) / (x2 - x1)
            return {
                "mode": "interpolated",
                "x": float(x),
                "x1": float(x1),
                "x2": float(x2),
                "y1": float(y1),
                "y2": float(y2),
                "result": float(result),
            }

    return {
        "mode": "upper_bound",
        "x": float(x),
        "x1": float(x_values[-1]),
        "x2": float(x_values[-1]),
        "y1": float(y_values[-1]),
        "y2": float(y_values[-1]),
        "result": float(y_values[-1]),
    }


def get_fa(PGA_S0, soil_class):
    if soil_class == "S5":
        return None
    return interpolate_table_value(PGA_S0, FA_X, FA_TABLE[soil_class])


def get_fv(PGA_S0, soil_class):
    if soil_class == "S5":
        return None
    return interpolate_table_value(PGA_S0, FV_X, FV_TABLE[soil_class])


def get_fa_detail(PGA_S0, soil_class):
    if soil_class == "S5":
        return None
    return get_interpolation_detail(PGA_S0, FA_X, FA_TABLE[soil_class])


def get_fv_detail(PGA_S0, soil_class):
    if soil_class == "S5":
        return None
    return get_interpolation_detail(PGA_S0, FV_X, FV_TABLE[soil_class])


def get_importance_factor(structure_type, ie_manual=None):
    info = STRUCTURE_TYPES[structure_type]
    if info["ie"] is not None:
        return float(info["ie"]), "Se asigno segun el tipo de estructura seleccionado."
    return float(ie_manual), "El usuario ingreso manualmente el factor de importancia para Tipo I."


def get_structural_system_values(system_name, manual_R=None, manual_Cd=None, manual_deriva=None):
    info = STRUCTURAL_SYSTEMS[system_name]
    if info["R"] is not None:
        return float(info["R"]), float(info["Cd"]), float(info["deriva_max"]), "Se asignaron segun el sistema estructural seleccionado."
    return float(manual_R), float(manual_Cd), float(manual_deriva), "El usuario ingreso manualmente R, Cd y deriva maxima."


def calculate_topographic_factor(mode, tau_manual=None, H=None, I=None, i=None):
    if mode == "Sin efecto topografico: tau = 1.00":
        return 1.0, {
            "justification": "No se considero amplificacion topografica especial.",
            "a": None,
            "b": None,
            "c": None,
        }

    if mode == "Ingresar tau manualmente":
        return float(tau_manual), {
            "justification": "El usuario ingreso manualmente el factor topografico.",
            "a": None,
            "b": None,
            "c": None,
        }

    H = float(H)
    I = float(I)
    i = float(i)
    a = H / 3.0
    b = min(20.0 * I, (H + 10.0) / 4.0)
    c = H / 4.0

    if H < 10.0 or i > (1.0 / 3.0):
        tau = 1.0
    else:
        diferencia = I - i
        if diferencia < 0.40:
            tau = 1.0
        elif 0.40 <= diferencia <= 0.90:
            tau = 1.0 + 0.80 * (diferencia - 0.40)
        else:
            tau = 1.40

    return float(tau), {
        "justification": "Se calculo a partir de las pendientes y altura del relieve.",
        "a": a,
        "b": b,
        "c": c,
    }


def _cds_by_fa(FaS0, structure_code):
    if structure_code == "IV":
        if FaS0 < 0.067:
            return "A"
        if 0.067 <= FaS0 < 0.133:
            return "C"
        return "D"

    if FaS0 < 0.067:
        return "A"
    if 0.067 <= FaS0 < 0.133:
        return "B"
    if 0.133 <= FaS0 < 0.200:
        return "C"
    return "D"


def _cds_by_fv(FvS0, structure_code):
    if structure_code == "IV":
        if FvS0 < 0.054:
            return "A"
        if 0.054 <= FvS0 < 0.106:
            return "C"
        return "D"

    if FvS0 < 0.054:
        return "A"
    if 0.054 <= FvS0 < 0.106:
        return "B"
    if 0.106 <= FvS0 < 0.160:
        return "C"
    return "D"


def calculate_cds(PGA_S0, Fa, Fv, structure_code):
    FaS0 = Fa * PGA_S0
    FvS0 = Fv * PGA_S0

    cds_fa = _cds_by_fa(FaS0, structure_code)
    cds_fv = _cds_by_fv(FvS0, structure_code)

    cds_final = cds_fa if CDS_ORDER[cds_fa] >= CDS_ORDER[cds_fv] else cds_fv

    if structure_code in {"I", "II", "III"} and PGA_S0 >= 0.330:
        cds_final = "E"
    if structure_code == "IV" and PGA_S0 >= 0.330:
        cds_final = "F"

    return cds_fa, cds_fv, cds_final, FaS0, FvS0


def calculate_characteristic_periods(Fa, Fv):
    T0 = 0.15 * Fv / Fa
    Ts = 0.50 * Fv / Fa
    TL = 4.00 * Fv / Fa
    return T0, Ts, TL


def calculate_sae(T, PGA_S0, Fa, Fv, T0, Ts, TL):
    T = np.asarray(T, dtype=float)
    Sae = np.zeros_like(T, dtype=float)

    mask1 = T < T0
    Sae[mask1] = Fa * PGA_S0 * (1 + 1.5 * T[mask1] / T0)

    mask2 = (T >= T0) & (T <= Ts)
    Sae[mask2] = 2.5 * Fa * PGA_S0

    mask3 = (T > Ts) & (T <= TL)
    Sae[mask3] = 1.25 * Fv * PGA_S0 / T[mask3]

    mask4 = T > TL
    Sae[mask4] = 1.25 * Fv * PGA_S0 * TL / (T[mask4] ** 2)

    return Sae


def _sae_at_period(T, PGA_S0, Fa, Fv, T0, Ts, TL):
    return float(calculate_sae(np.array([T], dtype=float), PGA_S0, Fa, Fv, T0, Ts, TL)[0])


def calcular_espectro(PGA_S0, Fa, Fv, Ie, tau, R, Tmin=0.0, Tmax=6.5, dT=0.01):
    if PGA_S0 <= 0:
        raise ValueError("PGA_S0 debe ser mayor que cero.")
    if PGA_S0 > 1:
        raise ValueError("PGA_S0 debe ingresarse como fraccion de g. Ejemplo: 0.16, no 16.")
    if Fa <= 0 or Fv <= 0:
        raise ValueError("Fa y Fv deben ser mayores que cero.")
    if R <= 0:
        raise ValueError("R debe ser mayor que cero.")
    if Tmax <= Tmin:
        raise ValueError("Tmax debe ser mayor que Tmin.")
    if dT <= 0:
        raise ValueError("dT debe ser mayor que cero.")

    T0 = 0.15 * Fv / Fa
    Ts = 0.50 * Fv / Fa
    TL = 4.00 * Fv / Fa

    T = np.arange(Tmin, Tmax + dT, dT)
    Sae = calculate_sae(T, PGA_S0, Fa, Fv, T0, Ts, TL)
    Sa = Sae * Ie * tau / R

    df = pd.DataFrame({
        "T_s": np.round(T, 4),
        "Sae_elastico_g": np.round(Sae, 5),
        "Sa_diseno_g": np.round(Sa, 5),
    })

    return df, T0, Ts, TL


def calculate_spectrum(PGA_S0, Fa, Fv, Ie, tau, R, Tmin, Tmax, dT):
    return calcular_espectro(PGA_S0, Fa, Fv, Ie, tau, R, Tmin, Tmax, dT)


def graficar_espectros(df, T0, Ts, TL):
    fig, ax = plt.subplots(figsize=(9, 5))

    ax.plot(df["T_s"], df["Sae_elastico_g"], label="Espectro elastico Sae", linewidth=2)
    ax.plot(df["T_s"], df["Sa_diseno_g"], label="Espectro de diseno Sa", linewidth=2)

    ax.axvline(T0, linestyle="--", label=f"T0 = {T0:.3f} s")
    ax.axvline(Ts, linestyle="--", label=f"Ts = {Ts:.3f} s")
    ax.axvline(TL, linestyle="--", label=f"TL = {TL:.3f} s")

    ax.set_xlabel("Periodo T (s)")
    ax.set_ylabel("Aceleracion espectral (g)")
    ax.set_title("Espectros sismicos NBDS 2023")
    ax.grid(True)
    ax.legend()
    fig.tight_layout()
    return fig


def create_spectrum_plot(df, T0, Ts, TL):
    return graficar_espectros(df, T0, Ts, TL)


def export_excel(df):
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Espectro")
    return buffer.getvalue()


def _find_value_at_period(df, target_period):
    idx = (df["T_s"] - target_period).abs().idxmin()
    return float(df.loc[idx, "Sae_elastico_g"]), float(df.loc[idx, "Sa_diseno_g"])


def _control_table(results, df):
    sae_1, sa_1 = _find_value_at_period(df, 1.0)
    sae_2, sa_2 = _find_value_at_period(df, 2.0)
    return pd.DataFrame(
        [
            ["T0", f"{results['T0']:.5f} s"],
            ["Ts", f"{results['Ts']:.5f} s"],
            ["TL", f"{results['TL']:.5f} s"],
            ["Sae(0)", f"{results['Sae_0']:.5f} g"],
            ["Sa(0)", f"{results['Sa_0']:.5f} g"],
            ["Sae maximo", f"{results['Sae_max']:.5f} g"],
            ["Sa diseno maximo", f"{results['Sa_max']:.5f} g"],
            ["Sae en T = 1 s", f"{sae_1:.5f} g"],
            ["Sa en T = 1 s", f"{sa_1:.5f} g"],
            ["Sae en T = 2 s", f"{sae_2:.5f} g"],
            ["Sa en T = 2 s", f"{sa_2:.5f} g"],
        ],
        columns=["Parametro", "Valor"],
    )


def _concept_rows(results):
    rows = [
        {
            "Parametro": "PGA_S0",
            "Valor": f"{results['PGA_S0']:.5f}",
            "Concepto": "Representa la aceleracion maxima probable del suelo del sitio, expresada como fraccion de g.",
            "Justificacion": "Valor ingresado por el usuario segun el mapa de amenaza sismica de la NBDS 2023.",
            "Metodo": "Entrada del usuario",
        },
        {
            "Parametro": "Tipo de suelo",
            "Valor": results["soil_class"],
            "Concepto": "Clasifica el terreno de fundacion y controla la amplificacion sismica local.",
            "Justificacion": "Se selecciono directamente en la interfaz.",
            "Metodo": "Seleccion del usuario",
        },
        {
            "Parametro": "Fa",
            "Valor": f"{results['Fa']:.5f}",
            "Concepto": "Coeficiente de sitio para periodos cortos. Modifica la zona de aceleracion constante del espectro.",
            "Justificacion": results["Fa_justification"],
            "Metodo": results["Fa_method"],
        },
        {
            "Parametro": "Fv",
            "Valor": f"{results['Fv']:.5f}",
            "Concepto": "Coeficiente de sitio para periodos largos. Modifica la rama descendente del espectro.",
            "Justificacion": results["Fv_justification"],
            "Metodo": results["Fv_method"],
        },
        {
            "Parametro": "Ie",
            "Valor": f"{results['Ie']:.5f}",
            "Concepto": "Factor de importancia. Incrementa la demanda sismica en estructuras cuyo funcionamiento o seguridad es mas critico.",
            "Justificacion": results["Ie_justification"],
            "Metodo": results["Ie_method"],
        },
        {
            "Parametro": "tau",
            "Valor": f"{results['tau']:.5f}",
            "Concepto": "Factor topografico. Amplifica la demanda sismica cuando la edificacion se ubica cerca de crestas o pendientes significativas.",
            "Justificacion": results["tau_justification"],
            "Metodo": results["tau_method"],
        },
        {
            "Parametro": "R",
            "Valor": f"{results['R']:.5f}",
            "Concepto": "Factor de reduccion de respuesta. Representa la capacidad de disipacion de energia y ductilidad del sistema estructural.",
            "Justificacion": results["system_justification"],
            "Metodo": results["system_method"],
        },
        {
            "Parametro": "Cd",
            "Valor": f"{results['Cd']:.5f}",
            "Concepto": "Factor de amplificacion de desplazamientos. Se usa para estimar desplazamientos sismicos inelasticos.",
            "Justificacion": results["system_justification"],
            "Metodo": results["system_method"],
        },
        {
            "Parametro": "Deriva maxima",
            "Valor": f"{results['deriva_max']:.5f}",
            "Concepto": "Deriva maxima admisible del sistema estructural seleccionado.",
            "Justificacion": results["system_justification"],
            "Metodo": results["system_method"],
        },
        {
            "Parametro": "T0",
            "Valor": f"{results['T0']:.5f}",
            "Concepto": "Periodo inicial del espectro, limite entre la rama ascendente y la meseta.",
            "Justificacion": "Se calculo con T0 = 0.15 * Fv / Fa.",
            "Metodo": "Formula NBDS 2023",
        },
        {
            "Parametro": "Ts",
            "Valor": f"{results['Ts']:.5f}",
            "Concepto": "Periodo de transicion entre la meseta de aceleracion constante y la rama de velocidad constante.",
            "Justificacion": "Se calculo con Ts = 0.50 * Fv / Fa.",
            "Metodo": "Formula NBDS 2023",
        },
        {
            "Parametro": "TL",
            "Valor": f"{results['TL']:.5f}",
            "Concepto": "Periodo largo de transicion hacia la rama controlada por desplazamiento.",
            "Justificacion": "Se calculo con TL = 4.00 * Fv / Fa.",
            "Metodo": "Formula NBDS 2023",
        },
        {
            "Parametro": "Sae",
            "Valor": "Variable con T",
            "Concepto": "Aceleracion espectral elastica para cada periodo T.",
            "Justificacion": "Se calculo por tramos segun la NBDS 2023.",
            "Metodo": "Formula NBDS 2023",
        },
        {
            "Parametro": "Sa",
            "Valor": "Variable con T",
            "Concepto": "Aceleracion espectral de diseno obtenida reduciendo Sae por R y considerando Ie y tau.",
            "Justificacion": "Se calculo con Sa = Sae * Ie * tau / R.",
            "Metodo": "Formula NBDS 2023",
        },
        {
            "Parametro": "CDS",
            "Valor": results["CDS_final"],
            "Concepto": "Categoria de diseno sismico que resume el nivel de exigencia sismica segun amenaza, suelo e importancia.",
            "Justificacion": "Se tomo la categoria mas desfavorable entre FaS0 y FvS0 y luego se aplicaron las reglas especiales por PGA_S0.",
            "Metodo": "Clasificacion NBDS 2023",
        },
    ]
    return pd.DataFrame(rows)


def _representative_table(results):
    rep_periods = [0.0, results["T0"], results["Ts"], results["TL"], results["Tmax"]]
    unique_periods = []
    for p in rep_periods:
        if not any(abs(p - q) < 1e-9 for q in unique_periods):
            unique_periods.append(p)

    arr = np.array(unique_periods, dtype=float)
    sae = calculate_sae(arr, results["PGA_S0"], results["Fa"], results["Fv"], results["T0"], results["Ts"], results["TL"])
    sa = sae * results["Ie"] * results["tau"] / results["R"]
    return pd.DataFrame({
        "T = s": np.round(arr, 4),
        "Sae_elastico_g": np.round(sae, 5),
        "Sa_diseno_g": np.round(sa, 5),
    })


def _pdf_table(rows, col_widths, font_size=8, header=True):
    table = Table(rows, colWidths=col_widths)
    style = [
        ("GRID", (0, 0), (-1, -1), 0.35, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), font_size),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]
    if header:
        style.append(("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey))
    table.setStyle(TableStyle(style))
    return table


def _table_from_dict_matrix(x_values, table_dict):
    headers = ["Suelo"] + [f"{value:.3f}" for value in x_values]
    rows = [headers]
    for soil_key in ["S0", "S1", "S2", "S3", "S4"]:
        rows.append([soil_key] + [f"{value:.3f}" for value in table_dict[soil_key]])
    return rows


def _interpolation_rows(parameter_name, detail, method_label):
    rows = [["Parametro", "Dato", "Valor"]]
    if detail is None:
        rows.extend([
            [parameter_name, "Metodo", method_label],
            [parameter_name, "Observacion", "No aplica interpolacion automatica para este caso."],
        ])
        return rows

    rows.append([parameter_name, "Metodo", method_label])
    rows.append([parameter_name, "PGA_S0 evaluado", f"{detail['x']:.5f}"])
    rows.append([parameter_name, "Punto inferior x1", f"{detail['x1']:.5f}"])
    rows.append([parameter_name, "Punto superior x2", f"{detail['x2']:.5f}"])
    rows.append([parameter_name, "Valor inferior y1", f"{detail['y1']:.5f}"])
    rows.append([parameter_name, "Valor superior y2", f"{detail['y2']:.5f}"])
    rows.append([parameter_name, "Resultado", f"{detail['result']:.5f}"])

    if detail["mode"] == "interpolated":
        expression = (
            f"y = {detail['y1']:.5f} + ({detail['y2']:.5f} - {detail['y1']:.5f}) * "
            f"({detail['x']:.5f} - {detail['x1']:.5f}) / ({detail['x2']:.5f} - {detail['x1']:.5f})"
        )
        rows.append([parameter_name, "Formula aplicada", expression])
    elif detail["mode"] == "exact":
        rows.append([parameter_name, "Formula aplicada", "PGA_S0 coincide exactamente con un punto tabulado; se adopta el valor directo de la tabla sin interpolar."])
    elif detail["mode"] == "lower_bound":
        rows.append([parameter_name, "Formula aplicada", "PGA_S0 menor o igual al minimo tabulado; se adopta el primer valor de la tabla."])
    else:
        rows.append([parameter_name, "Formula aplicada", "PGA_S0 mayor o igual al maximo tabulado; se adopta el ultimo valor de la tabla."])

    return rows


def create_pdf_report(results, spectrum_df, concept_df, fig):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.2 * cm,
        bottomMargin=1.2 * cm,
    )
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("Reporte tecnico de espectro sismico - NBDS 2023", styles["Title"]))
    story.append(Spacer(1, 0.3 * cm))

    project_rows = [
        ["Nombre del proyecto", results["project_name"] or "-"],
        ["Ubicacion", results["location"] or "-"],
        ["Fecha de generacion", datetime.now().strftime("%Y-%m-%d %H:%M")],
        ["Responsable", results["responsible"] or "-"],
    ]
    story.append(_pdf_table(project_rows, [5 * cm, 11 * cm], header=False))
    story.append(Spacer(1, 0.3 * cm))

    input_rows = [
        ["Parametro", "Valor"],
        ["PGA_S0", f"{results['PGA_S0']:.5f} g"],
        ["Tipo de suelo", results["soil_class"]],
        ["Metodo Fa/Fv", results["Fa_method"]],
        ["Fa", f"{results['Fa']:.5f}"],
        ["Fv", f"{results['Fv']:.5f}"],
        ["Tipo de estructura", results["structure_type"]],
        ["Ie", f"{results['Ie']:.5f}"],
        ["Sistema estructural", results["system_name"]],
        ["R", f"{results['R']:.5f}"],
        ["Cd", f"{results['Cd']:.5f}"],
        ["Deriva maxima", f"{results['deriva_max']:.5f}"],
        ["tau", f"{results['tau']:.5f}"],
        ["Tmin", f"{results['Tmin']:.4f} s"],
        ["Tmax", f"{results['Tmax']:.4f} s"],
        ["dT", f"{results['dT']:.4f} s"],
    ]
    story.append(Paragraph("Datos de entrada", styles["Heading2"]))
    story.append(_pdf_table(input_rows, [7 * cm, 9 * cm]))
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("Base normativa para coeficientes de sitio", styles["Heading2"]))
    story.append(Paragraph("Tabla Fa de la NBDS 2023", styles["Heading3"]))
    fa_rows = _table_from_dict_matrix(FA_X, FA_TABLE)
    story.append(_pdf_table(fa_rows, [1.6 * cm] + [2.35 * cm] * 6, font_size=7))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph("Tabla Fv de la NBDS 2023", styles["Heading3"]))
    fv_rows = _table_from_dict_matrix(FV_X, FV_TABLE)
    story.append(_pdf_table(fv_rows, [1.6 * cm] + [2.35 * cm] * 6, font_size=7))
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("Detalle tecnico de obtencion de Fa y Fv", styles["Heading2"]))
    story.append(Paragraph("Fa", styles["Heading3"]))
    fa_detail_rows = _interpolation_rows("Fa", results.get("Fa_interpolation"), results["Fa_method"])
    story.append(_pdf_table(fa_detail_rows, [2.0 * cm, 3.4 * cm, 10.1 * cm], font_size=7))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph("Fv", styles["Heading3"]))
    fv_detail_rows = _interpolation_rows("Fv", results.get("Fv_interpolation"), results["Fv_method"])
    story.append(_pdf_table(fv_detail_rows, [2.0 * cm, 3.4 * cm, 10.1 * cm], font_size=7))
    story.append(Spacer(1, 0.3 * cm))

    result_rows = [
        ["Parametro", "Valor"],
        ["T0", f"{results['T0']:.5f} s"],
        ["Ts", f"{results['Ts']:.5f} s"],
        ["TL", f"{results['TL']:.5f} s"],
        ["CDS final", results["CDS_final"]],
        ["Sae maximo", f"{results['Sae_max']:.5f} g"],
        ["Sa diseno maximo", f"{results['Sa_max']:.5f} g"],
    ]
    story.append(Paragraph("Resultados principales", styles["Heading2"]))
    story.append(_pdf_table(result_rows, [7 * cm, 9 * cm]))
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("Desarrollo numerico de formulas", styles["Heading2"]))
    development_lines = [
        f"Fa * PGA_S0 = {results['Fa']:.5f} * {results['PGA_S0']:.5f} = {results['FaS0']:.5f}",
        f"Fv * PGA_S0 = {results['Fv']:.5f} * {results['PGA_S0']:.5f} = {results['FvS0']:.5f}",
        f"T0 = 0.15 * Fv / Fa = 0.15 * {results['Fv']:.5f} / {results['Fa']:.5f} = {results['T0']:.5f} s",
        f"Ts = 0.50 * Fv / Fa = 0.50 * {results['Fv']:.5f} / {results['Fa']:.5f} = {results['Ts']:.5f} s",
        f"TL = 4.00 * Fv / Fa = 4.00 * {results['Fv']:.5f} / {results['Fa']:.5f} = {results['TL']:.5f} s",
        f"Sae(0) = Fa * PGA_S0 = {results['Fa']:.5f} * {results['PGA_S0']:.5f} = {results['Sae_0']:.5f} g",
        f"Sa(0) = Sae(0) * Ie * tau / R = {results['Sae_0']:.5f} * {results['Ie']:.5f} * {results['tau']:.5f} / {results['R']:.5f} = {results['Sa_0']:.5f} g",
        f"Meseta elastica = 2.5 * Fa * PGA_S0 = 2.5 * {results['Fa']:.5f} * {results['PGA_S0']:.5f} = {results['Sae_max']:.5f} g",
        f"Meseta de diseno = meseta elastica * Ie * tau / R = {results['Sae_max']:.5f} * {results['Ie']:.5f} * {results['tau']:.5f} / {results['R']:.5f} = {results['Sa_max']:.5f} g",
    ]
    for line in development_lines:
        story.append(Paragraph(line, styles["BodyText"]))
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("Concepto y justificacion de cada valor", styles["Heading2"]))
    concept_rows = [concept_df.columns.tolist()] + concept_df.astype(str).values.tolist()
    story.append(_pdf_table(concept_rows, [2.8 * cm, 2.1 * cm, 5.1 * cm, 4.9 * cm, 1.7 * cm], font_size=6))
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("Metodo de obtencion de Fa y Fv", styles["Heading2"]))
    method_rows = [
        ["Parametro", "Metodo"],
        ["Fa", results["Fa_method"]],
        ["Fv", results["Fv_method"]],
    ]
    story.append(_pdf_table(method_rows, [7 * cm, 9 * cm]))
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("Formulas usadas", styles["Heading2"]))
    formulas = [
        "T0 = 0.15 * Fv / Fa",
        "Ts = 0.50 * Fv / Fa",
        "TL = 4.00 * Fv / Fa",
        "Si T < T0: Sae = Fa * PGA_S0 * (1 + 1.5 * T / T0)",
        "Si T0 <= T <= Ts: Sae = 2.5 * Fa * PGA_S0",
        "Si Ts < T <= TL: Sae = 1.25 * Fv * PGA_S0 / T",
        "Si T > TL: Sae = 1.25 * Fv * PGA_S0 * TL / T^2",
        "Sa = Sae * Ie * tau / R",
    ]
    for formula in formulas:
        story.append(Paragraph(formula, styles["BodyText"]))
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("Interpretacion por tramos del espectro", styles["Heading2"]))
    tramo_rows = [
        ["Tramo", "Dominio", "Expresion", "Comentario tecnico"],
        ["1", f"0 <= T < {results['T0']:.5f} s", "Sae = Fa * PGA_S0 * (1 + 1.5 * T / T0)", "Rama ascendente inicial; parte en Sae(0) = Fa * PGA_S0."],
        ["2", f"{results['T0']:.5f} <= T <= {results['Ts']:.5f} s", "Sae = 2.5 * Fa * PGA_S0", "Meseta de aceleracion espectral constante."],
        ["3", f"{results['Ts']:.5f} < T <= {results['TL']:.5f} s", "Sae = 1.25 * Fv * PGA_S0 / T", "Rama descendente controlada por velocidad."],
        ["4", f"T > {results['TL']:.5f} s", "Sae = 1.25 * Fv * PGA_S0 * TL / T^2", "Rama descendente controlada por desplazamiento."],
    ]
    story.append(_pdf_table(tramo_rows, [1.1 * cm, 4.2 * cm, 5.2 * cm, 5.2 * cm], font_size=7))
    story.append(Spacer(1, 0.3 * cm))

    image_buffer = BytesIO()
    fig.savefig(image_buffer, format="png", dpi=180, bbox_inches="tight")
    image_buffer.seek(0)
    story.append(Paragraph("Grafica", styles["Heading2"]))
    story.append(Image(image_buffer, width=16 * cm, height=8.5 * cm))
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("Tabla reducida del espectro", styles["Heading2"]))
    rep_df = _representative_table(results)
    rep_rows = [rep_df.columns.tolist()] + rep_df.astype(str).values.tolist()
    story.append(_pdf_table(rep_rows, [4 * cm, 5 * cm, 5 * cm]))
    story.append(Paragraph("La tabla completa del espectro puede descargarse en CSV, Excel o TXT desde la pestana Tabla del espectro.", styles["BodyText"]))
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("Advertencias", styles["Heading2"]))
    warnings = []
    if results["soil_class"] == "S5":
        warnings.append("Advertencia: el suelo S5 requiere analisis especial de respuesta de sitio.")
    if results["Fa_method"] != "Automatico NBDS 2023 con interpolacion lineal" or results["Fv_method"] != "Automatico NBDS 2023 con interpolacion lineal":
        warnings.append("Advertencia: Fa y Fv fueron ingresados manualmente y deben verificarse con estudio tecnico.")
    warnings.append("Este reporte es una herramienta de apoyo al calculo. El diseno final debe ser revisado y firmado por un profesional competente.")
    for warning in warnings:
        story.append(Paragraph(warning, styles["BodyText"]))

    doc.build(story)
    return buffer.getvalue()


def _run_verification_case():
    df, T0, Ts, TL = calcular_espectro(
        PGA_S0=0.160,
        Fa=get_fa(0.160, "S2"),
        Fv=get_fv(0.160, "S2"),
        Ie=1.30000,
        tau=1.08000,
        R=5.00000,
        Tmin=0.0,
        Tmax=6.5,
        dT=0.01,
    )
    fa = get_fa(0.160, "S2")
    fv = get_fv(0.160, "S2")
    sae_0 = _sae_at_period(0.0, 0.160, fa, fv, T0, Ts, TL)
    sa_0 = sae_0 * 1.30000 * 1.08000 / 5.00000
    sae_1 = float(df.loc[(df["T_s"] - 1.0).abs().idxmin(), "Sae_elastico_g"])
    sa_1 = float(df.loc[(df["T_s"] - 1.0).abs().idxmin(), "Sa_diseno_g"])
    sae_2 = float(df.loc[(df["T_s"] - 2.0).abs().idxmin(), "Sae_elastico_g"])
    sa_2 = float(df.loc[(df["T_s"] - 2.0).abs().idxmin(), "Sa_diseno_g"])
    return {
        "Fa": fa,
        "Fv": fv,
        "T0": T0,
        "Ts": Ts,
        "TL": TL,
        "Sae_0": sae_0,
        "Sa_0": sa_0,
        "Sae_max": float(df["Sae_elastico_g"].max()),
        "Sa_max": float(df["Sa_diseno_g"].max()),
        "Sae_1": sae_1,
        "Sa_1": sa_1,
        "Sae_2": sae_2,
        "Sa_2": sa_2,
    }


def main():
    st.set_page_config(page_title="Espectro sismico NBDS 2023", layout="wide")
    st.title("Espectro sismico NBDS 2023")
    st.caption("Aplicacion tecnica para el calculo del espectro sismico segun la Norma Boliviana de Diseno Sismico NBDS 2023.")

    tabs = st.tabs([
        "Datos de entrada",
        "Resultados",
        "Tabla del espectro",
        "Grafica del espectro",
        "Reporte PDF",
    ])

    with tabs[0]:
        st.subheader("Datos del proyecto")
        c1, c2, c3 = st.columns(3)
        project_name = c1.text_input("Nombre del proyecto", "")
        location = c2.text_input("Ubicacion", "")
        responsible = c3.text_input("Responsable", "")

        st.subheader("Datos sismicos basicos")
        c1, c2 = st.columns(2)
        PGA_S0 = c1.number_input(
            "Aceleracion maxima del suelo PGA_S0",
            min_value=0.0,
            value=0.160,
            step=0.001,
            format="%.3f",
            help="Valor obtenido del mapa de amenaza sismica de la NBDS 2023, expresado como fraccion de g. Ejemplo: 0.16.",
        )
        structure_type = c2.selectbox("Tipo de estructura", list(STRUCTURE_TYPES.keys()))

        st.subheader("Coeficientes de sitio Fa y Fv")
        c1, c2 = st.columns(2)
        ffv_method = c1.selectbox("Metodo para Fa y Fv", ["Automatico segun NBDS 2023", "Manual / avanzado"])
        soil_option = c2.selectbox(
            "Tipo de suelo",
            [
                "S0 - Roca dura",
                "S1 - Roca",
                "S2 - Suelo muy rigido o roca blanda",
                "S3 - Suelo rigido",
                "S4 - Suelo blando",
                "S5 - Requiere analisis especial de respuesta de sitio",
            ],
        )
        soil_class = soil_option.split(" - ")[0]

        fa = None
        fv = None
        fa_interpolation = None
        fv_interpolation = None
        fa_method = ""
        fv_method = ""
        fa_fv_mode_label = ""
        fa_justification = ""
        fv_justification = ""

        if ffv_method == "Automatico segun NBDS 2023" and soil_class != "S5":
            fa = get_fa(PGA_S0, soil_class)
            fv = get_fv(PGA_S0, soil_class)
            fa_interpolation = get_fa_detail(PGA_S0, soil_class)
            fv_interpolation = get_fv_detail(PGA_S0, soil_class)
            fa_method = "Automatico NBDS 2023 con interpolacion lineal"
            fv_method = "Automatico NBDS 2023 con interpolacion lineal"
            fa_fv_mode_label = "Automatico NBDS 2023 con interpolacion lineal"
            fa_justification = "Se obtuvo automaticamente de la tabla Fa de la NBDS 2023 para el suelo seleccionado y PGA_S0 ingresado, aplicando interpolacion lineal cuando corresponde."
            fv_justification = "Se obtuvo automaticamente de la tabla Fv de la NBDS 2023 para el suelo seleccionado y PGA_S0 ingresado, aplicando interpolacion lineal cuando corresponde."
            st.info("Fa y Fv calculados automaticamente segun tablas NBDS 2023 e interpolacion lineal.")
            c1, c2 = st.columns(2)
            c1.number_input("Fa calculado", value=float(fa), format="%.5f", disabled=True)
            c2.number_input("Fv calculado", value=float(fv), format="%.5f", disabled=True)
        elif ffv_method == "Automatico segun NBDS 2023" and soil_class == "S5":
            st.warning("El suelo S5 requiere analisis especial de respuesta de sitio. Ingrese Fa y Fv manualmente segun estudio geotecnico/sismico.")
            c1, c2 = st.columns(2)
            fa = c1.number_input("Fa manual para suelo S5", min_value=0.0, value=1.00000, step=0.01, format="%.5f")
            fv = c2.number_input("Fv manual para suelo S5", min_value=0.0, value=1.00000, step=0.01, format="%.5f")
            fa_interpolation = None
            fv_interpolation = None
            fa_method = "Manual por suelo S5"
            fv_method = "Manual por suelo S5"
            fa_fv_mode_label = "Manual por suelo S5"
            fa_justification = "Valor ingresado manualmente porque el suelo S5 requiere estudio tecnico especial."
            fv_justification = "Valor ingresado manualmente porque el suelo S5 requiere estudio tecnico especial."
        else:
            st.warning("Modo manual activado. Verifique que los valores ingresados correspondan a un estudio tecnico o criterio profesional.")
            c1, c2 = st.columns(2)
            fa = c1.number_input("Fa manual", min_value=0.0, value=1.00000, step=0.01, format="%.5f")
            fv = c2.number_input("Fv manual", min_value=0.0, value=1.00000, step=0.01, format="%.5f")
            fa_interpolation = None
            fv_interpolation = None
            fa_method = "Manual / avanzado"
            fv_method = "Manual / avanzado"
            fa_fv_mode_label = "Manual / avanzado"
            fa_justification = "Valor ingresado manualmente por el usuario. Debe verificarse con estudio tecnico o criterio profesional."
            fv_justification = "Valor ingresado manualmente por el usuario. Debe verificarse con estudio tecnico o criterio profesional."

        st.subheader("Factor de importancia")
        if STRUCTURE_TYPES[structure_type]["ie"] is None:
            Ie_manual = st.number_input("Ie manual", min_value=0.0, value=1.00000, step=0.01, format="%.5f")
        else:
            Ie_manual = None

        st.subheader("Sistema estructural")
        system_name = st.selectbox("Sistema estructural", list(STRUCTURAL_SYSTEMS.keys()))
        if system_name == "Manual":
            c1, c2, c3 = st.columns(3)
            R_manual = c1.number_input("R manual", min_value=0.0, value=5.00000, step=0.01, format="%.5f")
            Cd_manual = c2.number_input("Cd manual", min_value=0.0, value=4.50000, step=0.01, format="%.5f")
            drift_manual = c3.number_input("Deriva maxima manual", min_value=0.0, value=0.01000, step=0.001, format="%.5f")
        else:
            R_manual = None
            Cd_manual = None
            drift_manual = None

        st.subheader("Factor topografico tau")
        tau_mode = st.selectbox(
            "Selector de tau",
            [
                "Sin efecto topografico: tau = 1.00",
                "Ingresar tau manualmente",
                "Calcular tau por pendiente",
            ],
        )
        tau_manual = None
        H = None
        I = None
        i = None
        if tau_mode == "Ingresar tau manualmente":
            tau_manual = st.number_input("tau manual", min_value=0.0, value=1.00000, step=0.01, format="%.5f")
        elif tau_mode == "Calcular tau por pendiente":
            c1, c2, c3 = st.columns(3)
            H = c1.number_input("H (m)", min_value=0.0, value=20.0, step=1.0, format="%.2f")
            I = c2.number_input("I pendiente cuesta abajo", min_value=0.0, value=0.60, step=0.01, format="%.3f")
            i = c3.number_input("i pendiente cuesta arriba", min_value=0.0, value=0.10, step=0.01, format="%.3f")

        st.subheader("Rango de periodos")
        c1, c2, c3 = st.columns(3)
        Tmin = c1.number_input("Tmin (s)", min_value=0.0, value=0.0000, step=0.01, format="%.4f")
        Tmax = c2.number_input("Tmax (s)", min_value=0.0, value=5.0000, step=0.1, format="%.4f")
        dT = c3.number_input("dT (s)", min_value=0.0, value=0.0100, step=0.01, format="%.4f")

    errors = []
    if PGA_S0 <= 0:
        errors.append("PGA_S0 debe ser mayor que 0.")
    if PGA_S0 > 1:
        errors.append("PGA_S0 debe ingresarse como fraccion de g. Ejemplo: 0.16, no 16.")
    if fa is None or fa <= 0:
        errors.append("Fa debe ser mayor que 0.")
    if fv is None or fv <= 0:
        errors.append("Fv debe ser mayor que 0.")
    if soil_class == "S5" and (fa is None or fv is None):
        errors.append("Si soil_class = S5 debes ingresar Fa y Fv manuales.")
    if Tmax <= Tmin:
        errors.append("Tmax debe ser mayor que Tmin.")
    if dT <= 0:
        errors.append("dT debe ser mayor que 0.")

    results = None
    spectrum_df = None
    concept_df = None
    control_df = None
    fig = None

    if not errors:
        try:
            Ie, ie_justification = get_importance_factor(structure_type, Ie_manual)
            R, Cd, deriva_max, system_justification = get_structural_system_values(
                system_name, R_manual, Cd_manual, drift_manual
            )
            tau, tau_info = calculate_topographic_factor(tau_mode, tau_manual, H, I, i)

            if R <= 0:
                errors.append("R debe ser mayor que 0.")
            else:
                spectrum_df, T0, Ts, TL = calculate_spectrum(PGA_S0, fa, fv, Ie, tau, R, Tmin, Tmax, dT)
                fig = graficar_espectros(spectrum_df, T0, Ts, TL)
                cds_fa, cds_fv, cds_final, FaS0, FvS0 = calculate_cds(
                    PGA_S0, fa, fv, STRUCTURE_TYPES[structure_type]["code"]
                )

                results = {
                    "project_name": project_name,
                    "location": location,
                    "responsible": responsible,
                    "PGA_S0": float(PGA_S0),
                    "soil_class": soil_class,
                    "structure_type": structure_type,
                    "system_name": system_name,
                    "Fa": float(fa),
                    "Fv": float(fv),
                    "FaS0": float(FaS0),
                    "FvS0": float(FvS0),
                    "FaFv_mode_label": fa_fv_mode_label,
                    "Fa_method": fa_method,
                    "Fv_method": fv_method,
                    "Fa_interpolation": fa_interpolation,
                    "Fv_interpolation": fv_interpolation,
                    "Fa_justification": fa_justification,
                    "Fv_justification": fv_justification,
                    "Ie": float(Ie),
                    "Ie_justification": ie_justification,
                    "Ie_method": "Automatico segun tipo de estructura" if STRUCTURE_TYPES[structure_type]["ie"] is not None else "Manual",
                    "tau": float(tau),
                    "tau_justification": tau_info["justification"],
                    "tau_method": (
                        "Sin efecto topografico" if tau_mode == "Sin efecto topografico: tau = 1.00"
                        else "Manual" if tau_mode == "Ingresar tau manualmente"
                        else "Calculado por pendiente"
                    ),
                    "R": float(R),
                    "Cd": float(Cd),
                    "deriva_max": float(deriva_max),
                    "system_justification": system_justification,
                    "system_method": "Automatico segun sistema estructural" if system_name != "Manual" else "Manual",
                    "T0": float(T0),
                    "Ts": float(Ts),
                    "TL": float(TL),
                    "CDS_fa": cds_fa,
                    "CDS_fv": cds_fv,
                    "CDS_final": cds_final,
                    "Tmin": float(Tmin),
                    "Tmax": float(Tmax),
                    "dT": float(dT),
                    "Sae_0": _sae_at_period(0.0, PGA_S0, fa, fv, T0, Ts, TL),
                    "Sa_0": _sae_at_period(0.0, PGA_S0, fa, fv, T0, Ts, TL) * Ie * tau / R,
                    "Sae_max": float(spectrum_df["Sae_elastico_g"].max()),
                    "Sa_max": float(spectrum_df["Sa_diseno_g"].max()),
                }

                concept_df = _concept_rows(results)
                control_df = _control_table(results, spectrum_df)
        except Exception as exc:
            errors.append(str(exc))

    verification = _run_verification_case()

    with tabs[1]:
        st.subheader("Resultados")
        if errors:
            for err in errors:
                st.error(err)
        else:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Fa", f"{results['Fa']:.5f}")
            c2.metric("Fv", f"{results['Fv']:.5f}")
            c3.metric("CDS final", results["CDS_final"])
            c4.metric("Sa diseno maximo", f"{results['Sa_max']:.5f} g")

            st.markdown("### Datos ingresados")
            input_df = pd.DataFrame(
                [
                    ["PGA_S0", f"{results['PGA_S0']:.5f} g"],
                    ["Tipo de suelo", results["soil_class"]],
                    ["Metodo Fa/Fv", results["FaFv_mode_label"]],
                    ["Tipo de estructura", structure_type],
                    ["Sistema estructural", system_name],
                    ["Condicion topografica", tau_mode],
                    ["Tmin", f"{Tmin:.4f} s"],
                    ["Tmax", f"{Tmax:.4f} s"],
                    ["dT", f"{dT:.4f} s"],
                ],
                columns=["Parametro", "Valor"],
            )
            st.table(input_df)

            st.markdown("### Coeficientes calculados")
            coef_df = pd.DataFrame(
                [
                    ["Fa", f"{results['Fa']:.5f}"],
                    ["Fv", f"{results['Fv']:.5f}"],
                    ["Fa * PGA_S0", f"{results['FaS0']:.5f}"],
                    ["Fv * PGA_S0", f"{results['FvS0']:.5f}"],
                    ["Ie", f"{results['Ie']:.5f}"],
                    ["tau", f"{results['tau']:.5f}"],
                    ["R", f"{results['R']:.5f}"],
                    ["Cd", f"{results['Cd']:.5f}"],
                    ["Deriva maxima", f"{results['deriva_max']:.5f}"],
                    ["T0", f"{results['T0']:.5f} s"],
                    ["Ts", f"{results['Ts']:.5f} s"],
                    ["TL", f"{results['TL']:.5f} s"],
                    ["CDS por Fa", results["CDS_fa"]],
                    ["CDS por Fv", results["CDS_fv"]],
                    ["CDS final", results["CDS_final"]],
                ],
                columns=["Parametro", "Valor"],
            )
            st.table(coef_df)

            st.markdown("### Tabla de control")
            st.table(control_df)

            st.markdown("### Concepto tecnico, justificacion y metodo")
            st.dataframe(concept_df, use_container_width=True, hide_index=True)

            with st.expander("Caso de verificacion obligatorio"):
                ver_df = pd.DataFrame(
                    [
                        ["Fa", f"{verification['Fa']:.5f}", "Esperado aprox.", "1.25970"],
                        ["Fv", f"{verification['Fv']:.5f}", "Esperado", "1.50000"],
                        ["T0", f"{verification['T0']:.5f}", "Esperado aprox.", "0.17861"],
                        ["Ts", f"{verification['Ts']:.5f}", "Esperado aprox.", "0.59538"],
                        ["TL", f"{verification['TL']:.5f}", "Esperado aprox.", "4.76303"],
                        ["Sae(0)", f"{verification['Sae_0']:.5f}", "Esperado aprox.", "0.20155"],
                        ["Sa(0)", f"{verification['Sa_0']:.5f}", "Esperado aprox.", "0.05660"],
                        ["Sae maximo", f"{verification['Sae_max']:.5f}", "Esperado aprox.", "0.50388"],
                        ["Sa diseno maximo", f"{verification['Sa_max']:.5f}", "Esperado aprox.", "0.14149"],
                        ["Sae en T = 1 s", f"{verification['Sae_1']:.5f}", "Esperado aprox.", "0.30000"],
                        ["Sa en T = 1 s", f"{verification['Sa_1']:.5f}", "Esperado aprox.", "0.08424"],
                        ["Sae en T = 2 s", f"{verification['Sae_2']:.5f}", "Esperado aprox.", "0.15000"],
                        ["Sa en T = 2 s", f"{verification['Sa_2']:.5f}", "Esperado aprox.", "0.04212"],
                    ],
                    columns=["Parametro", "Calculado", "Referencia", "Valor esperado"],
                )
                st.table(ver_df)

    with tabs[2]:
        st.subheader("Tabla del espectro")
        if errors:
            st.info("Corrige los datos de entrada para generar la tabla.")
        else:
            st.dataframe(spectrum_df, use_container_width=True, hide_index=True)
            csv_bytes = spectrum_df.to_csv(index=False).encode("utf-8")
            txt_bytes = spectrum_df.to_csv(index=False, sep="\t").encode("utf-8")
            xlsx_bytes = export_excel(spectrum_df)
            c1, c2, c3 = st.columns(3)
            c1.download_button("Descargar CSV", csv_bytes, file_name="espectro_nbds2023.csv", mime="text/csv")
            c2.download_button("Descargar Excel XLSX", xlsx_bytes, file_name="espectro_nbds2023.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            c3.download_button("Descargar TXT", txt_bytes, file_name="espectro_nbds2023.txt", mime="text/plain")

    with tabs[3]:
        st.subheader("Grafica del espectro")
        if errors:
            st.info("Corrige los datos de entrada para generar la grafica.")
        else:
            st.pyplot(fig, use_container_width=True)
            png_buffer = BytesIO()
            fig.savefig(png_buffer, format="png", dpi=180, bbox_inches="tight")
            st.download_button("Descargar grafica PNG", png_buffer.getvalue(), file_name="grafica_espectro_nbds2023.png", mime="image/png")

    with tabs[4]:
        st.subheader("Reporte PDF")
        if errors:
            st.info("Corrige los datos de entrada para generar el reporte.")
        else:
            pdf_bytes = create_pdf_report(results, spectrum_df, concept_df, fig)
            st.download_button("Generar reporte PDF", pdf_bytes, file_name="reporte_espectro_nbds2023.pdf", mime="application/pdf")

        st.markdown(
            """
**Instrucciones para ejecutar la app**

```bash
pip install streamlit pandas numpy matplotlib reportlab openpyxl
streamlit run app.py
```
"""
        )


if __name__ == "__main__":
    main()
