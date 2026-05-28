from domain.vigas_core import (
    DatosViga,
    calcular_viga,
    check_separacion_cype,
)


NORMA = {
    "phi_flex": 0.90,
    "phi_shear": 0.75,
    "phi_torsion": 0.75,
    "nombre": "ACI 318-19",
}


def _base_datos(**overrides):
    data = dict(
        modo="Diseñar / estimar acero con cargas",
        norma=NORMA,
        tipo_apoyo="Simplemente apoyada",
        luz_mm=6000.0,
        bw_mm=300.0,
        h_mm=550.0,
        rec_mm=30.0,
        db_estribo_mm=8.0,
        dag_mm=19.0,
        fc=28.0,
        fy=420.0,
        fyt=420.0,
        wu_kN_m=22.0,
        P_kN=0.0,
        x_p_mm=3000.0,
        Mu_pos_kNm=120.0,
        Mu_neg_i_kNm=80.0,
        Mu_neg_d_kNm=80.0,
        Vu_i_kN=95.0,
        Vu_d_kN=95.0,
        Tu_kNm=0.0,
        Pu_kN=0.0,
        n_inf=3,
        n_sup_i=2,
        n_sup_d=2,
        db_inf_mm=16.0,
        db_sup_i_mm=16.0,
        db_sup_d_mm=16.0,
        ramas=2,
        s_est_mm=150.0,
    )
    data.update(overrides)
    return DatosViga(**data)


def test_caso_flexion_con_mu_positivo():
    resultado = calcular_viga(_base_datos(Mu_pos_kNm=150.0))
    assert resultado.as_inf_mm2 > 0
    assert resultado.phi_mn_pos_kNm >= 150.0


def test_caso_sin_torsion():
    resultado = calcular_viga(_base_datos(Tu_kNm=0.0))
    assert resultado.phi_tn_kNm == 0.0
    assert resultado.ratio_t is None


def test_caso_cortante():
    resultado = calcular_viga(_base_datos(Vu_i_kN=120.0, Vu_d_kN=120.0))
    assert resultado.av_s_req_final > 0
    assert resultado.phi_vn_i_kN > 0


def test_separacion_libre_entre_barras():
    check = check_separacion_cype(300.0, 30.0, 8.0, 19.0, 3, 16.0, "Inferior")
    assert check["cumple"] is True
    assert check["s_libre_mm"] > check["sl_min_mm"]


def test_no_cumple_por_flexion():
    datos = _base_datos(
        modo="Verificar capacidad con acero ingresado",
        n_inf=2,
        db_inf_mm=12.0,
        Mu_pos_kNm=400.0,
    )
    resultado = calcular_viga(datos)
    assert resultado.cumple_global is False
    assert resultado.ratio_flex_pos is not None and resultado.ratio_flex_pos > 1.0


def test_cumple_en_caso_razonable():
    resultado = calcular_viga(_base_datos())
    assert resultado.cumple_global is True
