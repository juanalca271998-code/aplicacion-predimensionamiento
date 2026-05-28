import math

import numpy as np
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QGridLayout,
    QMessageBox,
    QGroupBox,
    QComboBox,
    QTabWidget,
    QScrollArea,
)

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from data.storage import guardar_resultado, obtener_configuracion


class ZapatasView(QWidget):
    def __init__(self):
        super().__init__()

        self.config = obtener_configuracion()
        self.unidad_fuerza = self.config.get("unidad_fuerza", "kN")
        self.unidad_momento = self.config.get("unidad_momento", "kN·m")
        self.unidad_longitud = self.config.get("unidad_longitud", "mm")
        self.unidad_area_acero = self.config.get("unidad_area_acero", "mm²")
        self.ultimo_resultado = {}
        self.diametros_disponibles_mm = [12, 14, 16, 18, 20, 22, 25, 28]

        self.normas = {
            "ACI 318-19": {"phi_flex": 0.90, "phi_shear": 0.75, "nombre": "ACI 318-19"},
            "ACI 318-25": {"phi_flex": 0.90, "phi_shear": 0.75, "nombre": "ACI 318-25"},
            "NB 1225001": {"phi_flex": 0.90, "phi_shear": 0.75, "nombre": "NB 1225001"},
        }

        layout = QVBoxLayout(self)
        titulo = QLabel("MODULO ZAPATAS - DISENO PRELIMINAR DE CIMENTACIONES")
        titulo.setStyleSheet("font-size: 16px; font-weight: bold; padding: 4px;")
        layout.addWidget(titulo)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self.tab_datos = QWidget()
        self.tab_comp = QWidget()
        self.tab_res = QWidget()
        self.tab_gra = QWidget()
        self.tabs.addTab(self.tab_datos, "Datos")
        self.tabs.addTab(self.tab_comp, "Comprobaciones")
        self.tabs.addTab(self.tab_res, "Resultados")
        self.tabs.addTab(self.tab_gra, "Graficos")

        self._crear_tab_datos()
        self._crear_tab_comprobaciones()
        self._crear_tab_resultados()
        self._crear_tab_graficos()
        self._actualizar_tipo_zapata()

    # ======================================================
    # UI
    # ======================================================
    def _crear_tab_datos(self):
        outer = QVBoxLayout(self.tab_datos)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        outer.addWidget(scroll)
        cont = QWidget()
        scroll.setWidget(cont)
        layout = QVBoxLayout(cont)

        grupo_general = QGroupBox("1. Configuracion general")
        g = QGridLayout()
        self.modo = QComboBox()
        self.modo.addItems(["Predimensionar", "Verificar"])
        self.norma = QComboBox()
        self.norma.addItems(list(self.normas.keys()))
        self.tipo_zapata = QComboBox()
        self.tipo_zapata.addItems([
            "Zapata aislada rectangular",
            "Zapata aislada cuadrada",
            "Zapata corrida",
            "Zapata combinada rectangular",
        ])
        self.tipo_zapata.currentTextChanged.connect(self._actualizar_tipo_zapata)
        self.modo.currentTextChanged.connect(self._actualizar_tipo_zapata)
        self.relacion = QLineEdit("1.00")
        g.addWidget(QLabel("Modo"), 0, 0)
        g.addWidget(self.modo, 0, 1)
        g.addWidget(QLabel("Norma"), 1, 0)
        g.addWidget(self.norma, 1, 1)
        g.addWidget(QLabel("Tipo de zapata"), 2, 0)
        g.addWidget(self.tipo_zapata, 2, 1)
        g.addWidget(QLabel("Relacion L/B para predimensionar"), 3, 0)
        g.addWidget(self.relacion, 3, 1)
        grupo_general.setLayout(g)
        layout.addWidget(grupo_general)

        grupo_suelo = QGroupBox("2. Suelo y materiales")
        g = QGridLayout()
        self.qadm = QLineEdit("250")
        self.gamma_c = QLineEdit("24")
        self.fc = QLineEdit("28")
        self.fy = QLineEdit("420")
        g.addWidget(QLabel("q admisible del suelo (kPa = kN/m²)"), 0, 0)
        g.addWidget(self.qadm, 0, 1)
        g.addWidget(QLabel("Peso especifico hormigon (kN/m³)"), 1, 0)
        g.addWidget(self.gamma_c, 1, 1)
        g.addWidget(QLabel("f'c (MPa)"), 2, 0)
        g.addWidget(self.fc, 2, 1)
        g.addWidget(QLabel("fy (MPa)"), 3, 0)
        g.addWidget(self.fy, 3, 1)
        grupo_suelo.setLayout(g)
        layout.addWidget(grupo_suelo)

        grupo_cargas = QGroupBox("3. Envolvente de cargas para predimensionar / verificar")
        g = QGridLayout()
        self.n_serv = QLineEdit("900")
        self.mx_serv = QLineEdit("0")
        self.my_serv = QLineEdit("0")
        self.pu = QLineEdit("1350")
        self.mux = QLineEdit("0")
        self.muy = QLineEdit("0")

        self.n2_serv = QLineEdit("700")
        self.n2_u = QLineEdit("1050")
        self.sep_columnas = QLineEdit("3000")

        self.carga_lineal_serv = QLineEdit("300")
        self.carga_lineal_u = QLineEdit("450")

        self.cargas_help = QLabel(
            "Ingresa una sola envolvente representativa de tu software de diseno. "
            "El modulo la usa para predimensionar y para las comprobaciones preliminares."
        )
        self.cargas_help.setWordWrap(True)
        g.addWidget(self.cargas_help, 0, 0, 1, 2)
        g.addWidget(QLabel(f"Carga vertical envolvente N ({self.unidad_fuerza})"), 1, 0)
        g.addWidget(self.n_serv, 1, 1)
        g.addWidget(QLabel(f"Mx envolvente ({self.unidad_momento})"), 2, 0)
        g.addWidget(self.mx_serv, 2, 1)
        g.addWidget(QLabel(f"My envolvente ({self.unidad_momento})"), 3, 0)
        g.addWidget(self.my_serv, 3, 1)
        g.addWidget(QLabel(f"Carga columna 2 N2 ({self.unidad_fuerza})"), 4, 0)
        g.addWidget(self.n2_serv, 4, 1)
        g.addWidget(QLabel(f"Separacion entre columnas ({self.unidad_longitud})"), 5, 0)
        g.addWidget(self.sep_columnas, 5, 1)
        g.addWidget(QLabel(f"Carga lineal envolvente ({self.unidad_fuerza}/m)"), 6, 0)
        g.addWidget(self.carga_lineal_serv, 6, 1)
        grupo_cargas.setLayout(g)
        layout.addWidget(grupo_cargas)
        self.grupo_cargas = grupo_cargas

        grupo_geom = QGroupBox("4. Geometria")
        g = QGridLayout()
        self.c1 = QLineEdit("400")
        self.c2 = QLineEdit("400")
        self.c1b = QLineEdit("400")
        self.c2b = QLineEdit("400")
        self.b = QLineEdit("2000")
        self.l = QLineEdit("2000")
        self.h = QLineEdit("500")
        self.rec = QLineEdit("75")
        self.db = QLineEdit("16")
        self.ancho_corrida = QLineEdit("1200")

        g.addWidget(QLabel(f"Columna 1 c1 ({self.unidad_longitud})"), 0, 0)
        g.addWidget(self.c1, 0, 1)
        g.addWidget(QLabel(f"Columna 1 c2 ({self.unidad_longitud})"), 1, 0)
        g.addWidget(self.c2, 1, 1)
        g.addWidget(QLabel(f"Columna 2 c1 ({self.unidad_longitud})"), 2, 0)
        g.addWidget(self.c1b, 2, 1)
        g.addWidget(QLabel(f"Columna 2 c2 ({self.unidad_longitud})"), 3, 0)
        g.addWidget(self.c2b, 3, 1)
        g.addWidget(QLabel(f"Ancho B ({self.unidad_longitud})"), 4, 0)
        g.addWidget(self.b, 4, 1)
        g.addWidget(QLabel(f"Largo L ({self.unidad_longitud})"), 5, 0)
        g.addWidget(self.l, 5, 1)
        g.addWidget(QLabel(f"Canto h ({self.unidad_longitud})"), 6, 0)
        g.addWidget(self.h, 6, 1)
        g.addWidget(QLabel(f"Recubrimiento ({self.unidad_longitud})"), 7, 0)
        g.addWidget(self.rec, 7, 1)
        g.addWidget(QLabel(f"Diametro barra base ({self.unidad_longitud})"), 8, 0)
        g.addWidget(self.db, 8, 1)
        g.addWidget(QLabel(f"Ancho zapata corrida B ({self.unidad_longitud})"), 9, 0)
        g.addWidget(self.ancho_corrida, 9, 1)
        grupo_geom.setLayout(g)
        layout.addWidget(grupo_geom)
        self.grupo_geom = grupo_geom

        grupo_armado = QGroupBox("5. Parrilla de acero para verificacion")
        g = QGridLayout()
        self.n_barras_x = QLineEdit("10")
        self.db_x = QLineEdit("16")
        self.n_barras_y = QLineEdit("10")
        self.db_y = QLineEdit("16")
        g.addWidget(QLabel("Numero de barras direccion X"), 0, 0)
        g.addWidget(self.n_barras_x, 0, 1)
        g.addWidget(QLabel(f"Diametro barras X ({self.unidad_longitud})"), 1, 0)
        g.addWidget(self.db_x, 1, 1)
        g.addWidget(QLabel("Numero de barras direccion Y"), 2, 0)
        g.addWidget(self.n_barras_y, 2, 1)
        g.addWidget(QLabel(f"Diametro barras Y ({self.unidad_longitud})"), 3, 0)
        g.addWidget(self.db_y, 3, 1)
        grupo_armado.setLayout(g)
        layout.addWidget(grupo_armado)
        self.grupo_armado = grupo_armado

        botones = QHBoxLayout()
        self.btn_calc = QPushButton("Calcular")
        self.btn_calc.clicked.connect(self.calcular)
        self.btn_limpiar = QPushButton("Limpiar")
        self.btn_limpiar.clicked.connect(self.limpiar)
        self.btn_guardar = QPushButton("Guardar resultados")
        self.btn_guardar.clicked.connect(self.guardar)
        botones.addWidget(self.btn_calc)
        botones.addWidget(self.btn_limpiar)
        botones.addWidget(self.btn_guardar)
        layout.addLayout(botones)
        layout.addStretch()

    def _crear_tab_comprobaciones(self):
        layout = QVBoxLayout(self.tab_comp)
        self.texto_comp = QTextEdit()
        self.texto_comp.setReadOnly(True)
        layout.addWidget(self.texto_comp)

    def _crear_tab_resultados(self):
        layout = QVBoxLayout(self.tab_res)
        cuadro = QGroupBox("Cuadro de armadura preliminar / verificada")
        cuadro_layout = QVBoxLayout()
        self.texto_armado = QTextEdit()
        self.texto_armado.setReadOnly(True)
        cuadro_layout.addWidget(self.texto_armado)
        cuadro.setLayout(cuadro_layout)
        layout.addWidget(cuadro)
        self.texto_res = QTextEdit()
        self.texto_res.setReadOnly(True)
        layout.addWidget(self.texto_res)

    def _crear_tab_graficos(self):
        layout = QHBoxLayout(self.tab_gra)
        self.fig_2d = Figure(figsize=(6.4, 5.0))
        self.canvas_2d = FigureCanvas(self.fig_2d)
        self.fig_3d = Figure(figsize=(6.4, 5.0))
        self.canvas_3d = FigureCanvas(self.fig_3d)
        layout.addWidget(self.canvas_2d)
        layout.addWidget(self.canvas_3d)

    def _actualizar_tipo_zapata(self):
        tipo = self.tipo_zapata.currentText()
        es_combinada = tipo == "Zapata combinada rectangular"
        es_corrida = tipo == "Zapata corrida"
        es_cuadrada = tipo == "Zapata aislada cuadrada"
        es_rectangular = tipo == "Zapata aislada rectangular"

        for widget in [self.n2_serv, self.n2_u, self.sep_columnas, self.c1b, self.c2b]:
            widget.setEnabled(es_combinada)
        self.ancho_corrida.setEnabled(es_corrida)
        self.mx_serv.setEnabled(not es_corrida)
        self.my_serv.setEnabled(not es_corrida)
        self.mux.setEnabled(not es_corrida)
        self.muy.setEnabled(not es_corrida)
        self.b.setEnabled(not es_corrida)
        self.l.setEnabled(not es_cuadrada and not es_corrida)
        self.grupo_armado.setEnabled(self.modo.currentText() == "Verificar")

        if es_cuadrada:
            self.relacion.setText("1.00")
            self.relacion.setEnabled(False)
        else:
            self.relacion.setEnabled(True)
            if es_rectangular and abs(float(self.relacion.text() or "1.0") - 1.0) < 1e-9:
                self.relacion.setText("1.30")

    # ======================================================
    # CONVERSIONES
    # ======================================================
    def _l_to_mm(self, valor):
        if self.unidad_longitud == "mm":
            return valor
        if self.unidad_longitud == "cm":
            return valor * 10.0
        if self.unidad_longitud == "m":
            return valor * 1000.0
        return valor

    def _mm_to_user(self, valor_mm):
        if self.unidad_longitud == "mm":
            return valor_mm
        if self.unidad_longitud == "cm":
            return valor_mm / 10.0
        if self.unidad_longitud == "m":
            return valor_mm / 1000.0
        return valor_mm

    def _f_to_kN(self, valor):
        if self.unidad_fuerza == "kN":
            return valor
        if self.unidad_fuerza == "tf":
            return valor * 9.80665
        if self.unidad_fuerza == "kgf":
            return valor * 0.00980665
        return valor

    def _m_to_kNm(self, valor):
        if self.unidad_momento == "kN·m":
            return valor
        if self.unidad_momento == "tf·m":
            return valor * 9.80665
        if self.unidad_momento == "kgf·m":
            return valor * 0.00980665
        return valor

    def _area_show(self, area_mm2):
        if self.unidad_area_acero == "cm²":
            return area_mm2 / 100.0
        return area_mm2

    def _bar_area(self, db_mm):
        return math.pi * db_mm * db_mm / 4.0

    def _phi_mn_provisto(self, as_mm2, bw_mm, d_mm, fc, fy, phi):
        if as_mm2 <= 0 or bw_mm <= 0 or d_mm <= 0:
            return 0.0
        a = as_mm2 * fy / max(0.85 * fc * bw_mm, 1e-9)
        mn_nmm = as_mm2 * fy * max(d_mm - a / 2.0, 0.0)
        return phi * mn_nmm / 1e6

    def _redondear_dimension_m(self, valor_m, paso=0.05):
        return math.ceil(valor_m / paso) * paso

    def _generar_sugerencias_dimensiones(self, area_req_m2, tipo, relacion=1.0, sep_m=0.0, cmax_m=0.0):
        sugerencias = []
        if tipo == "Zapata corrida":
            base = self._redondear_dimension_m(area_req_m2, 0.05)
            for extra in [0.0, 0.10, 0.20]:
                valor = base + extra
                sugerencias.append({"B_m": valor, "L_m": 1.0, "texto": f"B = {valor:.2f} m por metro lineal"})
            return sugerencias

        if tipo == "Zapata aislada cuadrada":
            lado = self._redondear_dimension_m(math.sqrt(area_req_m2), 0.05)
            for extra in [0.0, 0.10, 0.20]:
                valor = lado + extra
                sugerencias.append({"B_m": valor, "L_m": valor, "texto": f"{valor:.2f} m x {valor:.2f} m"})
            return sugerencias

        if tipo == "Zapata combinada rectangular":
            base_rel = max(relacion, 1.5)
            b0 = math.sqrt(area_req_m2 / max(base_rel, 1e-9))
            l0 = max(area_req_m2 / max(b0, 1e-9), sep_m + cmax_m + 0.8)
            for extra_b, extra_l in [(0.0, 0.0), (0.10, 0.20), (0.20, 0.30)]:
                b = self._redondear_dimension_m(b0 + extra_b, 0.05)
                l = self._redondear_dimension_m(max(l0 + extra_l, area_req_m2 / max(b, 1e-9)), 0.05)
                sugerencias.append({"B_m": b, "L_m": l, "texto": f"{b:.2f} m x {l:.2f} m"})
            return sugerencias

        relaciones = []
        objetivo = max(relacion, 1.20)
        for rel in [1.20, objetivo, max(objetivo + 0.20, 1.45)]:
            if all(abs(rel - existente) > 1e-6 for existente in relaciones):
                relaciones.append(rel)
        for idx, rel in enumerate(relaciones):
            b0 = math.sqrt(area_req_m2 / max(rel, 1e-9))
            l0 = area_req_m2 / max(b0, 1e-9)
            extra = 0.10 * idx
            b = self._redondear_dimension_m(b0 + extra, 0.05)
            l = self._redondear_dimension_m(max(l0 + extra, area_req_m2 / max(b, 1e-9)), 0.05)
            sugerencias.append({
                "B_m": b,
                "L_m": l,
                "texto": f"{b:.2f} m x {l:.2f} m  (L/B ≈ {l / max(b, 1e-9):.2f})",
            })
        return sugerencias

    def _separacion_promedio_mm(self, ancho_mm, rec_mm, n_barras):
        if n_barras <= 1:
            return 0.0
        longitud_util = max(ancho_mm - 2.0 * rec_mm, 0.0)
        return longitud_util / max(n_barras - 1, 1)

    def _sugerir_malla(self, as_req_mm2, longitud_util_mm, rec_mm, diametro_base_mm):
        if as_req_mm2 <= 0:
            return {"texto": "No requerida", "as_prov_mm2": 0.0, "n_barras": 0, "db_mm": 0.0, "sep_mm": 0.0}

        diametros = sorted(set(self.diametros_disponibles_mm + [int(round(max(diametro_base_mm, 10.0)))]))
        mejor = None
        for db in diametros:
            area_barra = self._bar_area(db)
            n_barras = max(4, math.ceil(as_req_mm2 / max(area_barra, 1e-9)))
            sep_mm = self._separacion_promedio_mm(longitud_util_mm, rec_mm, n_barras)
            as_prov = n_barras * area_barra
            candidato = {
                "texto": f"{n_barras} Ø{db}  (sep. aprox. {sep_mm:.0f} mm)",
                "as_prov_mm2": as_prov,
                "n_barras": n_barras,
                "db_mm": float(db),
                "sep_mm": sep_mm,
            }
            if mejor is None or as_prov < mejor["as_prov_mm2"]:
                mejor = candidato
        return mejor

    # ======================================================
    # LECTURA / VALIDACION
    # ======================================================
    def _leer_datos(self):
        n_env = self._f_to_kN(float(self.n_serv.text()))
        mx_env = self._m_to_kNm(float(self.mx_serv.text()))
        my_env = self._m_to_kNm(float(self.my_serv.text()))
        n2_env = self._f_to_kN(float(self.n2_serv.text()))
        w_env = self._f_to_kN(float(self.carga_lineal_serv.text()))
        return {
            "modo": self.modo.currentText(),
            "norma": self.normas[self.norma.currentText()],
            "tipo": self.tipo_zapata.currentText(),
            "relacion": float(self.relacion.text()),
            "qadm_kPa": float(self.qadm.text()),
            "gamma_c_kN_m3": float(self.gamma_c.text()),
            "fc": float(self.fc.text()),
            "fy": float(self.fy.text()),
            "N_serv_kN": n_env,
            "Mx_serv_kNm": mx_env,
            "My_serv_kNm": my_env,
            "Pu_kN": n_env,
            "Mux_kNm": mx_env,
            "Muy_kNm": my_env,
            "N2_serv_kN": n2_env,
            "N2_u_kN": n2_env,
            "sep_cols_mm": self._l_to_mm(float(self.sep_columnas.text())),
            "w_serv_kN_m": w_env,
            "w_u_kN_m": w_env,
            "c1_mm": self._l_to_mm(float(self.c1.text())),
            "c2_mm": self._l_to_mm(float(self.c2.text())),
            "c1b_mm": self._l_to_mm(float(self.c1b.text())),
            "c2b_mm": self._l_to_mm(float(self.c2b.text())),
            "B_mm": self._l_to_mm(float(self.b.text())),
            "L_mm": self._l_to_mm(float(self.l.text())),
            "h_mm": self._l_to_mm(float(self.h.text())),
            "rec_mm": self._l_to_mm(float(self.rec.text())),
            "db_mm": self._l_to_mm(float(self.db.text())),
            "Bcorr_mm": self._l_to_mm(float(self.ancho_corrida.text())),
            "n_barras_x": int(float(self.n_barras_x.text())),
            "db_x_mm": self._l_to_mm(float(self.db_x.text())),
            "n_barras_y": int(float(self.n_barras_y.text())),
            "db_y_mm": self._l_to_mm(float(self.db_y.text())),
        }

    def _validar(self, d):
        if d["qadm_kPa"] <= 0:
            raise ValueError("La presion admisible del suelo debe ser mayor que cero.")
        if d["fc"] <= 0 or d["fy"] <= 0:
            raise ValueError("f'c y fy deben ser mayores que cero.")
        if d["h_mm"] <= 0 or d["rec_mm"] < 0 or d["db_mm"] <= 0:
            raise ValueError("h, recubrimiento y diametro deben ser validos.")
        if d["tipo"] in {"Zapata aislada rectangular", "Zapata aislada cuadrada"}:
            if d["N_serv_kN"] <= 0 or d["Pu_kN"] <= 0:
                raise ValueError("Las cargas verticales deben ser mayores que cero.")
            if d["c1_mm"] <= 0 or d["c2_mm"] <= 0:
                raise ValueError("Las dimensiones de la columna deben ser mayores que cero.")
        if d["tipo"] == "Zapata combinada rectangular":
            if min(d["N_serv_kN"], d["N2_serv_kN"], d["Pu_kN"], d["N2_u_kN"]) <= 0:
                raise ValueError("Las dos columnas deben tener cargas verticales validas.")
            if d["sep_cols_mm"] <= 0:
                raise ValueError("La separacion entre columnas debe ser mayor que cero.")
        if d["tipo"] == "Zapata corrida" and min(d["w_serv_kN_m"], d["w_u_kN_m"], d["Bcorr_mm"]) <= 0:
            raise ValueError("Para zapata corrida debes ingresar carga lineal y ancho validos.")
        if d["modo"] == "Verificar":
            if d["tipo"] == "Zapata corrida":
                if d["Bcorr_mm"] <= 0:
                    raise ValueError("El ancho de la zapata corrida debe ser mayor que cero.")
            else:
                if d["B_mm"] <= 0 or d["L_mm"] <= 0:
                    raise ValueError("B y L deben ser mayores que cero en modo verificacion.")
            if min(d["n_barras_x"], d["n_barras_y"], d["db_x_mm"], d["db_y_mm"]) <= 0:
                raise ValueError("En verificacion debes ingresar una parrilla valida en X e Y.")

    # ======================================================
    # CALCULO
    # ======================================================
    def _resolver_as(self, mu_kNm, bw_mm, d_mm, fc, fy, phi):
        mu_nmm = max(mu_kNm, 0.0) * 1e6
        mn_req = mu_nmm / max(phi, 1e-9)
        if mn_req <= 0:
            return 0.0
        low = 0.0
        high = bw_mm * d_mm * 0.08
        for _ in range(120):
            mid = 0.5 * (low + high)
            a = mid * fy / max(0.85 * fc * bw_mm, 1e-9)
            mn = mid * fy * max(d_mm - a / 2.0, 0.0)
            if mn >= mn_req:
                high = mid
            else:
                low = mid
        return high

    def _rho_min(self, fc, fy):
        return max(0.0018, 0.25 * math.sqrt(fc) / max(fy, 1e-9))

    def _presiones_esquinas(self, n_kN, mx_kNm, my_kNm, B_m, L_m):
        ex_m = my_kNm / max(n_kN, 1e-9)
        ey_m = mx_kNm / max(n_kN, 1e-9)
        q0 = n_kN / max(B_m * L_m, 1e-9)
        fx = 6.0 * ex_m / max(B_m, 1e-9)
        fy = 6.0 * ey_m / max(L_m, 1e-9)
        esquinas = [
            q0 * (1 + fx + fy),
            q0 * (1 + fx - fy),
            q0 * (1 - fx + fy),
            q0 * (1 - fx - fy),
        ]
        return ex_m, ey_m, esquinas

    def _calcular_aislada(self, d):
        area_req_m2 = d["N_serv_kN"] / max(d["qadm_kPa"], 1e-9)
        sugerencias = self._generar_sugerencias_dimensiones(area_req_m2, d["tipo"], d["relacion"])
        if d["modo"] == "Predimensionar":
            if d["tipo"] == "Zapata aislada cuadrada":
                B_m = math.sqrt(area_req_m2)
                L_m = B_m
            else:
                relacion = max(d["relacion"], 1.20)
                B_m = math.sqrt(area_req_m2 / max(relacion, 1e-9))
                L_m = area_req_m2 / max(B_m, 1e-9)
            d["B_mm"] = B_m * 1000.0
            d["L_mm"] = L_m * 1000.0
            self.b.setText(f"{self._mm_to_user(d['B_mm']):.2f}")
            self.l.setText(f"{self._mm_to_user(d['L_mm']):.2f}")
        B_m = d["B_mm"] / 1000.0
        L_m = d["L_mm"] / 1000.0
        ex_s, ey_s, q_serv = self._presiones_esquinas(d["N_serv_kN"], d["Mx_serv_kNm"], d["My_serv_kNm"], B_m, L_m)
        ex_u, ey_u, q_u = self._presiones_esquinas(d["Pu_kN"], d["Mux_kNm"], d["Muy_kNm"], B_m, L_m)
        qmax = max(q_serv)
        qmin = min(q_serv)
        qmax_u = max(q_u)
        d_eff_mm = d["h_mm"] - d["rec_mm"] - d["db_mm"] / 2.0
        if d_eff_mm <= 0:
            raise ValueError("La profundidad efectiva resulto invalida.")
        d_eff_m = d_eff_mm / 1000.0
        a_x = max((B_m - d["c1_mm"] / 1000.0) / 2.0, 0.0)
        a_y = max((L_m - d["c2_mm"] / 1000.0) / 2.0, 0.0)
        mu_x = qmax_u * L_m * a_x * a_x / 2.0
        mu_y = qmax_u * B_m * a_y * a_y / 2.0
        return self._resolver_zapata_biaxial(d, B_m, L_m, qmax, qmin, qmax_u, d_eff_mm, d_eff_m, a_x, a_y, mu_x, mu_y, ex_s, ey_s, q_serv, sugerencias)

    def _resolver_zapata_biaxial(self, d, B_m, L_m, qmax, qmin, qmax_u, d_eff_mm, d_eff_m, a_x, a_y, mu_x, mu_y, ex_s, ey_s, q_serv, sugerencias):
        phi_flex = d["norma"]["phi_flex"]
        phi_shear = d["norma"]["phi_shear"]
        as_x = self._resolver_as(mu_x, d["L_mm"], d_eff_mm, d["fc"], d["fy"], phi_flex)
        as_y = self._resolver_as(mu_y, d["B_mm"], d_eff_mm, d["fc"], d["fy"], phi_flex)
        rho_min = self._rho_min(d["fc"], d["fy"])
        as_min_x = rho_min * d["L_mm"] * d_eff_mm
        as_min_y = rho_min * d["B_mm"] * d_eff_mm
        as_x = max(as_x, as_min_x)
        as_y = max(as_y, as_min_y)

        vu_1w_x = qmax_u * L_m * max(a_x - d_eff_m, 0.0)
        vu_1w_y = qmax_u * B_m * max(a_y - d_eff_m, 0.0)
        phi_vc_x = phi_shear * 0.17 * math.sqrt(d["fc"]) * d["L_mm"] * d_eff_mm / 1000.0
        phi_vc_y = phi_shear * 0.17 * math.sqrt(d["fc"]) * d["B_mm"] * d_eff_mm / 1000.0

        c1_m = d["c1_mm"] / 1000.0
        c2_m = d["c2_mm"] / 1000.0
        b0_mm = 2.0 * ((d["c1_mm"] + d_eff_mm) + (d["c2_mm"] + d_eff_mm))
        a_inside_m2 = (c1_m + d_eff_m) * (c2_m + d_eff_m)
        vu_punch = max(d["Pu_kN"] - qmax_u * a_inside_m2, 0.0)
        phi_vc_punch = phi_shear * 0.33 * math.sqrt(d["fc"]) * b0_mm * d_eff_mm / 1000.0
        as_prov_x = d["n_barras_x"] * self._bar_area(d["db_x_mm"]) if d["modo"] == "Verificar" else 0.0
        as_prov_y = d["n_barras_y"] * self._bar_area(d["db_y_mm"]) if d["modo"] == "Verificar" else 0.0
        phi_mn_x = self._phi_mn_provisto(as_prov_x, d["L_mm"], d_eff_mm, d["fc"], d["fy"], phi_flex) if d["modo"] == "Verificar" else 0.0
        phi_mn_y = self._phi_mn_provisto(as_prov_y, d["B_mm"], d_eff_mm, d["fc"], d["fy"], phi_flex) if d["modo"] == "Verificar" else 0.0
        arm_x = self._sugerir_malla(as_x, d["L_mm"], d["rec_mm"], d["db_mm"])
        arm_y = self._sugerir_malla(as_y, d["B_mm"], d["rec_mm"], d["db_mm"])

        return {
            "area_req_m2": d["N_serv_kN"] / max(d["qadm_kPa"], 1e-9),
            "sugerencias_dimensiones": sugerencias,
            "B_m": B_m,
            "L_m": L_m,
            "d_eff_mm": d_eff_mm,
            "q_serv": q_serv,
            "qmax_kPa": qmax,
            "qmin_kPa": qmin,
            "qmax_u_kPa": qmax_u,
            "ex_s_m": ex_s,
            "ey_s_m": ey_s,
            "Mu_x_kNm": mu_x,
            "Mu_y_kNm": mu_y,
            "As_x_mm2": as_x,
            "As_y_mm2": as_y,
            "As_min_x_mm2": as_min_x,
            "As_min_y_mm2": as_min_y,
            "As_prov_x_mm2": as_prov_x,
            "As_prov_y_mm2": as_prov_y,
            "phi_mn_x_kNm": phi_mn_x,
            "phi_mn_y_kNm": phi_mn_y,
            "phi_vc_x_kN": phi_vc_x,
            "phi_vc_y_kN": phi_vc_y,
            "Vu_1w_x_kN": vu_1w_x,
            "Vu_1w_y_kN": vu_1w_y,
            "phi_vc_punch_kN": phi_vc_punch,
            "Vu_punch_kN": vu_punch,
            "armadura_x": arm_x,
            "armadura_y": arm_y,
        }

    def _calcular_corrida(self, d):
        area_req_m2_por_m = d["w_serv_kN_m"] / max(d["qadm_kPa"], 1e-9)
        sugerencias = self._generar_sugerencias_dimensiones(area_req_m2_por_m, d["tipo"])
        if d["modo"] == "Predimensionar":
            d["Bcorr_mm"] = area_req_m2_por_m * 1000.0
            self.ancho_corrida.setText(f"{self._mm_to_user(d['Bcorr_mm']):.2f}")
        B_m = d["Bcorr_mm"] / 1000.0
        q_serv = d["w_serv_kN_m"] / max(B_m, 1e-9)
        q_u = d["w_u_kN_m"] / max(B_m, 1e-9)
        d_eff_mm = d["h_mm"] - d["rec_mm"] - d["db_mm"] / 2.0
        d_eff_m = d_eff_mm / 1000.0
        a = max((B_m - d["c1_mm"] / 1000.0) / 2.0, 0.0)
        mu = q_u * a * a / 2.0
        phi_flex = d["norma"]["phi_flex"]
        phi_shear = d["norma"]["phi_shear"]
        as_req = self._resolver_as(mu, 1000.0, d_eff_mm, d["fc"], d["fy"], phi_flex)
        as_min = self._rho_min(d["fc"], d["fy"]) * 1000.0 * d_eff_mm
        as_req = max(as_req, as_min)
        vu = q_u * max(a - d_eff_m, 0.0)
        phi_vc = phi_shear * 0.17 * math.sqrt(d["fc"]) * 1000.0 * d_eff_mm / 1000.0
        as_prov = d["n_barras_x"] * self._bar_area(d["db_x_mm"]) if d["modo"] == "Verificar" else 0.0
        phi_mn = self._phi_mn_provisto(as_prov, 1000.0, d_eff_mm, d["fc"], d["fy"], phi_flex) if d["modo"] == "Verificar" else 0.0
        arm = self._sugerir_malla(as_req, d["Bcorr_mm"], d["rec_mm"], d["db_mm"])
        return {
            "area_req_m2": area_req_m2_por_m,
            "sugerencias_dimensiones": sugerencias,
            "B_m": B_m,
            "L_m": 1.0,
            "d_eff_mm": d_eff_mm,
            "q_serv": [q_serv, q_serv, q_serv, q_serv],
            "qmax_kPa": q_serv,
            "qmin_kPa": q_serv,
            "qmax_u_kPa": q_u,
            "ex_s_m": 0.0,
            "ey_s_m": 0.0,
            "Mu_x_kNm": mu,
            "Mu_y_kNm": 0.0,
            "As_x_mm2": as_req,
            "As_y_mm2": as_req,
            "As_min_x_mm2": as_min,
            "As_min_y_mm2": as_min,
            "As_prov_x_mm2": as_prov,
            "As_prov_y_mm2": as_prov,
            "phi_mn_x_kNm": phi_mn,
            "phi_mn_y_kNm": phi_mn,
            "phi_vc_x_kN": phi_vc,
            "phi_vc_y_kN": phi_vc,
            "Vu_1w_x_kN": vu,
            "Vu_1w_y_kN": 0.0,
            "phi_vc_punch_kN": 0.0,
            "Vu_punch_kN": 0.0,
            "armadura_x": arm,
            "armadura_y": arm,
        }

    def _calcular_combinada(self, d):
        n_total = d["N_serv_kN"] + d["N2_serv_kN"]
        pu_total = d["Pu_kN"] + d["N2_u_kN"]
        area_req_m2 = n_total / max(d["qadm_kPa"], 1e-9)
        sep_m = d["sep_cols_mm"] / 1000.0
        sugerencias = self._generar_sugerencias_dimensiones(
            area_req_m2,
            d["tipo"],
            d["relacion"],
            sep_m,
            max(d["c1_mm"], d["c1b_mm"]) / 1000.0,
        )
        if d["modo"] == "Predimensionar":
            relacion = max(d["relacion"], 1.5)
            B_m = math.sqrt(area_req_m2 / max(relacion, 1e-9))
            L_m = max(area_req_m2 / max(B_m, 1e-9), sep_m + max(d["c1_mm"], d["c1b_mm"]) / 1000.0 + 0.8)
            d["B_mm"] = B_m * 1000.0
            d["L_mm"] = L_m * 1000.0
            self.b.setText(f"{self._mm_to_user(d['B_mm']):.2f}")
            self.l.setText(f"{self._mm_to_user(d['L_mm']):.2f}")
        B_m = d["B_mm"] / 1000.0
        L_m = d["L_mm"] / 1000.0

        x1 = L_m / 2.0 - sep_m / 2.0
        x2 = L_m / 2.0 + sep_m / 2.0
        xbar_serv = (d["N_serv_kN"] * x1 + d["N2_serv_kN"] * x2) / max(n_total, 1e-9)
        xbar_u = (d["Pu_kN"] * x1 + d["N2_u_kN"] * x2) / max(pu_total, 1e-9)
        ey_serv = xbar_serv - L_m / 2.0
        ey_u = xbar_u - L_m / 2.0
        q0_serv = n_total / max(B_m * L_m, 1e-9)
        q0_u = pu_total / max(B_m * L_m, 1e-9)
        fy_serv = 6.0 * ey_serv / max(L_m, 1e-9)
        fy_u = 6.0 * ey_u / max(L_m, 1e-9)
        q_serv = [
            q0_serv * (1 + fy_serv),
            q0_serv * (1 - fy_serv),
            q0_serv * (1 + fy_serv),
            q0_serv * (1 - fy_serv),
        ]
        q_u = [
            q0_u * (1 + fy_u),
            q0_u * (1 - fy_u),
            q0_u * (1 + fy_u),
            q0_u * (1 - fy_u),
        ]
        qmax = max(q_serv)
        qmin = min(q_serv)
        qmax_u = max(q_u)
        d_eff_mm = d["h_mm"] - d["rec_mm"] - d["db_mm"] / 2.0
        d_eff_m = d_eff_mm / 1000.0
        voladizo = max((L_m - sep_m - d["c1_mm"] / 1000.0 - d["c1b_mm"] / 1000.0) / 2.0, 0.0)
        mu_y = qmax_u * B_m * voladizo * voladizo / 2.0
        mu_x = qmax_u * L_m * max((B_m - max(d["c2_mm"], d["c2b_mm"]) / 1000.0) / 2.0, 0.0) ** 2 / 2.0
        base = self._resolver_zapata_biaxial(d, B_m, L_m, qmax, qmin, qmax_u, d_eff_mm, d_eff_m, max((B_m - d["c1_mm"] / 1000.0) / 2.0, 0.0), voladizo, mu_x, mu_y, 0.0, ey_serv, q_serv, sugerencias)
        base["x1_m"] = x1
        base["x2_m"] = x2
        return base

    def _diagnostico(self, d, r):
        if d["tipo"] == "Zapata corrida":
            ratio_mx = r["Mu_x_kNm"] / max(r["phi_mn_x_kNm"], 1e-9) if d["modo"] == "Verificar" and r["phi_mn_x_kNm"] > 0 else 0.0
            ratios = [
                r["qmax_kPa"] / max(d["qadm_kPa"], 1e-9),
                r["Vu_1w_x_kN"] / max(r["phi_vc_x_kN"], 1e-9),
                ratio_mx,
            ]
            if max(ratios) > 1.0:
                return "No cumple", "La zapata corrida no cumple preliminarmente. Revisa B o h."
            if max(ratios) >= 0.85:
                return "Cumple ajustado", "Cumple ajustado. Conviene revisar la solucion final."
            if max(ratios) >= 0.55:
                return "Cumple adecuadamente", "La zapata corrida presenta un comportamiento preliminar razonable."
            return "Posible sobredimensionamiento", "La zapata corrida podria optimizarse."

        ratio_mx = r["Mu_x_kNm"] / max(r["phi_mn_x_kNm"], 1e-9) if d["modo"] == "Verificar" and r["phi_mn_x_kNm"] > 0 else 0.0
        ratio_my = r["Mu_y_kNm"] / max(r["phi_mn_y_kNm"], 1e-9) if d["modo"] == "Verificar" and r["phi_mn_y_kNm"] > 0 else 0.0
        ratios = [
            r["qmax_kPa"] / max(d["qadm_kPa"], 1e-9),
            r["Vu_1w_x_kN"] / max(r["phi_vc_x_kN"], 1e-9),
            r["Vu_1w_y_kN"] / max(r["phi_vc_y_kN"], 1e-9),
            r["Vu_punch_kN"] / max(r["phi_vc_punch_kN"], 1e-9) if r["phi_vc_punch_kN"] > 0 else 0.0,
            ratio_mx,
            ratio_my,
        ]
        if r["qmin_kPa"] < 0:
            return "No cumple", "Hay traccion en parte de la base. La resultante cae fuera del nucleo central."
        if max(ratios) > 1.0:
            return "No cumple", "La cimentacion no cumple de forma preliminar. Aumenta dimensiones o canto."
        if max(ratios) >= 0.85:
            return "Cumple ajustado", "Cumple ajustado. Conviene revisar detalladamente con un modelo mas completo."
        if max(ratios) >= 0.55:
            return "Cumple adecuadamente", "La zapata presenta un rango preliminar razonable."
        return "Posible sobredimensionamiento", "La demanda es baja respecto de la capacidad preliminar."

    def _texto_armadura(self, d, r):
        lineas = [
            "=== CUADRO DE ARMADURA ===",
            "",
            f"As requerida X = {self._area_show(r['As_x_mm2']):.2f} {self.unidad_area_acero}",
            f"As requerida Y = {self._area_show(r['As_y_mm2']):.2f} {self.unidad_area_acero}",
            "",
            "Armadura preliminar sugerida:",
            f"- Malla X: {r['armadura_x']['texto']}  | As prov. = {self._area_show(r['armadura_x']['as_prov_mm2']):.2f} {self.unidad_area_acero}",
            f"- Malla Y: {r['armadura_y']['texto']}  | As prov. = {self._area_show(r['armadura_y']['as_prov_mm2']):.2f} {self.unidad_area_acero}",
        ]
        if d["modo"] == "Verificar":
            lineas.extend(
                [
                    "",
                    "Parrilla ingresada por el usuario:",
                    f"- X: {d['n_barras_x']} Ø{self._mm_to_user(d['db_x_mm']):.0f}  | As = {self._area_show(r['As_prov_x_mm2']):.2f} {self.unidad_area_acero}",
                    f"- Y: {d['n_barras_y']} Ø{self._mm_to_user(d['db_y_mm']):.0f}  | As = {self._area_show(r['As_prov_y_mm2']):.2f} {self.unidad_area_acero}",
                ]
            )
        return "\n".join(lineas)

    def calcular(self):
        try:
            self.texto_comp.clear()
            self.texto_res.clear()
            d = self._leer_datos()
            self._validar(d)

            if d["tipo"] in {"Zapata aislada rectangular", "Zapata aislada cuadrada"}:
                r = self._calcular_aislada(d)
            elif d["tipo"] == "Zapata corrida":
                r = self._calcular_corrida(d)
            else:
                r = self._calcular_combinada(d)

            categoria, mensaje = self._diagnostico(d, r)
            ratio_mx = r["Mu_x_kNm"] / max(r.get("phi_mn_x_kNm", 0.0), 1e-9) if d["modo"] == "Verificar" else 0.0
            ratio_my = r["Mu_y_kNm"] / max(r.get("phi_mn_y_kNm", 0.0), 1e-9) if d["modo"] == "Verificar" else 0.0

            comp = [
                "=== COMPROBACIONES PRELIMINARES DE CIMENTACION ===",
                "",
                f"1. qmax servicio = {r['qmax_kPa']:.2f} kPa {'OK' if r['qmax_kPa'] <= d['qadm_kPa'] else 'NO CUMPLE'}",
                f"2. qmin servicio = {r['qmin_kPa']:.2f} kPa {'OK' if r['qmin_kPa'] >= 0 else 'NO CUMPLE'}",
                f"3. Cortante unidireccional X Vu/φVc = {r['Vu_1w_x_kN'] / max(r['phi_vc_x_kN'], 1e-9):.3f} {'OK' if r['Vu_1w_x_kN'] <= r['phi_vc_x_kN'] else 'NO CUMPLE'}",
            ]
            if d["tipo"] != "Zapata corrida":
                comp.append(f"4. Cortante unidireccional Y Vu/φVc = {r['Vu_1w_y_kN'] / max(r['phi_vc_y_kN'], 1e-9):.3f} {'OK' if r['Vu_1w_y_kN'] <= r['phi_vc_y_kN'] else 'NO CUMPLE'}")
                comp.append(f"5. Punzonamiento Vu/φVc = {r['Vu_punch_kN'] / max(r['phi_vc_punch_kN'], 1e-9):.3f} {'OK' if r['Vu_punch_kN'] <= r['phi_vc_punch_kN'] else 'NO CUMPLE'}")
                comp.append(f"6. As minimo X = {self._area_show(r['As_min_x_mm2']):.2f} {self.unidad_area_acero}")
                comp.append(f"7. As minimo Y = {self._area_show(r['As_min_y_mm2']):.2f} {self.unidad_area_acero}")
                if d["modo"] == "Verificar":
                    comp.append(f"8. Flexion X Mu/phiMn = {ratio_mx:.3f} {'OK' if r['Mu_x_kNm'] <= r['phi_mn_x_kNm'] else 'NO CUMPLE'}")
                    comp.append(f"9. Flexion Y Mu/phiMn = {ratio_my:.3f} {'OK' if r['Mu_y_kNm'] <= r['phi_mn_y_kNm'] else 'NO CUMPLE'}")
            else:
                comp.append(f"4. As minimo longitudinal = {self._area_show(r['As_min_x_mm2']):.2f} {self.unidad_area_acero}")
                if d["modo"] == "Verificar":
                    comp.append(f"5. Flexion longitudinal Mu/phiMn = {ratio_mx:.3f} {'OK' if r['Mu_x_kNm'] <= r['phi_mn_x_kNm'] else 'NO CUMPLE'}")
            comp.append("")
            comp.append("=== DIAGNOSTICO FINAL ===")
            comp.append(f"- {categoria}: {mensaje}")
            self.texto_comp.setPlainText("\n".join(comp))
            self.texto_armado.setPlainText(self._texto_armadura(d, r))

            res = [
                "=== RESUMEN INGENIERIL DE CIMENTACION ===",
                "",
                f"Norma: {d['norma']['nombre']}",
                f"Modo: {d['modo']}",
                f"Tipo: {d['tipo']}",
                f"Area requerida por q adm = {r['area_req_m2']:.3f} m²",
                f"Dimensiones adoptadas: B = {r['B_m']:.3f} m ; L = {r['L_m']:.3f} m ; h = {d['h_mm'] / 1000.0:.3f} m",
                f"Profundidad efectiva d = {r['d_eff_mm']:.1f} mm",
                "",
                "Medidas sugeridas para uso preliminar:",
                *[f"- {item['texto']}" for item in r.get("sugerencias_dimensiones", [])],
                "",
                "Presiones de contacto de la envolvente (kPa):",
                f"- {', '.join(f'{q:.2f}' for q in r['q_serv'])}",
                f"- qmax = {r['qmax_kPa']:.2f} kPa",
                f"- qmin = {r['qmin_kPa']:.2f} kPa",
                "",
                "Flexion preliminar:",
                f"- Mu_x = {r['Mu_x_kNm']:.2f} kN·m",
                f"- Mu_y = {r['Mu_y_kNm']:.2f} kN·m",
                f"- As_x = {self._area_show(r['As_x_mm2']):.2f} {self.unidad_area_acero}",
                f"- As_y = {self._area_show(r['As_y_mm2']):.2f} {self.unidad_area_acero}",
                f"- Malla sugerida X = {r['armadura_x']['texto']}",
                f"- Malla sugerida Y = {r['armadura_y']['texto']}",
                "",
                "Capacidad con la parrilla ingresada:",
                f"- As provista X = {self._area_show(r.get('As_prov_x_mm2', 0.0)):.2f} {self.unidad_area_acero}",
                f"- As provista Y = {self._area_show(r.get('As_prov_y_mm2', 0.0)):.2f} {self.unidad_area_acero}",
                f"- phiMn X soportado = {r.get('phi_mn_x_kNm', 0.0):.2f} kN*m",
                f"- phiMn Y soportado = {r.get('phi_mn_y_kNm', 0.0):.2f} kN*m",
                "",
                "Cortante y punzonamiento:",
                f"- Vu 1W X = {r['Vu_1w_x_kN']:.2f} kN ; φVc X = {r['phi_vc_x_kN']:.2f} kN",
            ]
            if d["tipo"] != "Zapata corrida":
                res.extend([
                    f"- Vu 1W Y = {r['Vu_1w_y_kN']:.2f} kN ; φVc Y = {r['phi_vc_y_kN']:.2f} kN",
                    f"- Vu punzonamiento = {r['Vu_punch_kN']:.2f} kN ; φVc punzonamiento = {r['phi_vc_punch_kN']:.2f} kN",
                ])
            res.extend([
                "",
                "Notas tecnicas:",
                "- El modulo es preliminar y orientado al predimensionamiento y chequeo rapido con una sola envolvente de cargas.",
                "- Se consideran repartos de presion lineales segun excentricidades globales.",
                "- El tomo de Calavera revisado aporta referencias sobre enlace zapata-terreno flexible y criterios de predimensionamiento.",
                "- Para suelo altamente deformable, asentamientos diferenciales, rigidez del encepado o interaccion suelo-estructura, conviene un modelo mas completo.",
            ])
            self.texto_res.setPlainText("\n".join(res))

            self.ultimo_resultado = {
                "modulo": "zapatas",
                "tipo": d["tipo"],
                "norma": d["norma"]["nombre"],
                "cumple": categoria != "No cumple",
                "diagnostico": categoria,
                "armadura_texto": self.texto_armado.toPlainText(),
                "resumen_texto": "\n".join(res),
                "comprobaciones_texto": "\n".join(comp),
            }

            self._graficar_2d(d, r)
            self._graficar_3d(d, r)
            self.tabs.setCurrentWidget(self.tab_res)

        except Exception as e:
            QMessageBox.warning(self, "Error de datos", f"Revisa los valores ingresados.\n\n{e}")

    # ======================================================
    # GRAFICOS
    # ======================================================
    def _annot_dim_h(self, ax, x0, x1, y, text):
        ax.annotate("", xy=(x0, y), xytext=(x1, y), arrowprops=dict(arrowstyle="<->", color="black"))
        ax.text((x0 + x1) / 2.0, y, text, ha="center", va="bottom")

    def _annot_dim_v(self, ax, x, y0, y1, text):
        ax.annotate("", xy=(x, y0), xytext=(x, y1), arrowprops=dict(arrowstyle="<->", color="black"))
        ax.text(x, (y0 + y1) / 2.0, text, rotation=90, va="center", ha="left")

    def _draw_rect(self, ax, x0, y0, width, height, color="firebrick", linewidth=2, label=None):
        ax.plot(
            [x0, x0 + width, x0 + width, x0, x0],
            [y0, y0, y0 + height, y0 + height, y0],
            color=color,
            linewidth=linewidth,
        )
        if label:
            ax.text(x0 + width / 2.0, y0 + height / 2.0, label, ha="center", va="center", color=color, fontweight="bold")

    def _graficar_2d(self, d, r):
        self.fig_2d.clear()
        ax = self.fig_2d.add_subplot(111)

        tipo = d["tipo"]
        B = r["B_m"] * 1000.0
        L = r["L_m"] * 1000.0
        ax.plot([0, B, B, 0, 0], [0, 0, L, L, 0], color="black", linewidth=2)
        ax.fill([0, B, B, 0], [0, 0, L, L], color="#f3f1eb", alpha=0.75)

        if tipo == "Zapata corrida":
            c1 = d["c1_mm"]
            x0 = (B - c1) / 2.0
            y0 = 0.35 * L
            h_col = 0.30 * L
            self._draw_rect(ax, x0, y0, c1, h_col, label="Muro / columna")
            self._annot_dim_h(ax, x0, x0 + c1, y0 - 0.06 * L, f"c = {self._mm_to_user(c1):.1f} {self.unidad_longitud}")
        elif tipo == "Zapata combinada rectangular":
            sep = d["sep_cols_mm"]
            x1 = L / 2.0 - sep / 2.0
            x2 = L / 2.0 + sep / 2.0
            x_mid = B / 2.0
            c1a = d["c1_mm"]
            c2a = d["c2_mm"]
            c1b = d["c1b_mm"]
            c2b = d["c2b_mm"]
            self._draw_rect(ax, x_mid - c2a / 2.0, x1 - c1a / 2.0, c2a, c1a, color="firebrick", label="C1")
            self._draw_rect(ax, x_mid - c2b / 2.0, x2 - c1b / 2.0, c2b, c1b, color="darkred", label="C2")
            self._annot_dim_v(ax, -0.08 * B, x1, x2, f"sep = {self._mm_to_user(sep):.1f} {self.unidad_longitud}")
            self._annot_dim_h(ax, x_mid - c2a / 2.0, x_mid + c2a / 2.0, x1 - 0.10 * L, f"c2-1 = {self._mm_to_user(c2a):.1f} {self.unidad_longitud}")
            self._annot_dim_h(ax, x_mid - c2b / 2.0, x_mid + c2b / 2.0, x2 + 0.05 * L, f"c2-2 = {self._mm_to_user(c2b):.1f} {self.unidad_longitud}")
        else:
            c1 = d["c1_mm"]
            c2 = d["c2_mm"]
            x0 = (B - c1) / 2.0
            y0 = (L - c2) / 2.0
            self._draw_rect(ax, x0, y0, c1, c2, label="Col.")
            self._annot_dim_h(ax, x0, x0 + c1, y0 - 0.06 * L, f"c1 = {self._mm_to_user(c1):.1f} {self.unidad_longitud}")
            self._annot_dim_v(ax, x0 + c1 + 0.04 * B, y0, y0 + c2, f"c2 = {self._mm_to_user(c2):.1f} {self.unidad_longitud}")

        self._annot_dim_h(ax, 0, B, -0.08 * L, f"B = {self._mm_to_user(B):.1f} {self.unidad_longitud}")
        self._annot_dim_v(ax, -0.06 * B, 0, L, f"L = {self._mm_to_user(L):.1f} {self.unidad_longitud}")
        ax.text(B / 2.0, L + 0.07 * L, f"qmax = {r['qmax_kPa']:.1f} kPa", ha="center", fontweight="bold")
        ax.text(B / 2.0, L + 0.13 * L, f"qmin = {r['qmin_kPa']:.1f} kPa", ha="center")
        ax.text(
            B / 2.0,
            -0.15 * L,
            "Acotacion esquematica en planta - dimensiones adoptadas para evaluacion preliminar",
            ha="center",
            fontsize=8,
            color="dimgray",
        )

        ax.set_title("Planta y acotaciones de la cimentacion")
        ax.set_aspect("equal", adjustable="box")
        ax.set_xlim(-0.16 * B, 1.12 * B)
        ax.set_ylim(-0.16 * L, 1.18 * L)
        ax.grid(True, alpha=0.25)
        ax.set_xlabel("x (mm)")
        ax.set_ylabel("y (mm)")
        self.fig_2d.tight_layout()
        self.canvas_2d.draw()

    def _graficar_3d(self, d, r):
        self.fig_3d.clear()
        ax = self.fig_3d.add_subplot(111, projection="3d")

        B = r["B_m"]
        L = r["L_m"]
        x = np.linspace(0, B, 30)
        y = np.linspace(0, L, 30)
        X, Y = np.meshgrid(x, y)

        if d["tipo"] == "Zapata corrida":
            Z = np.full_like(X, r["qmax_kPa"])
        elif d["tipo"] == "Zapata combinada rectangular":
            q_izq = r["q_serv"][0]
            q_der = r["q_serv"][1]
            Z = q_izq + (q_der - q_izq) * (Y / max(L, 1e-9))
        else:
            q1, q2, q3, q4 = r["q_serv"]
            Z = (
                q1 * (1 - X / max(B, 1e-9)) * (1 - Y / max(L, 1e-9))
                + q2 * (X / max(B, 1e-9)) * (1 - Y / max(L, 1e-9))
                + q3 * (1 - X / max(B, 1e-9)) * (Y / max(L, 1e-9))
                + q4 * (X / max(B, 1e-9)) * (Y / max(L, 1e-9))
            )

        surf = ax.plot_surface(X, Y, Z, cmap="viridis", edgecolor="none", alpha=0.92)
        ax.contour(X, Y, Z, zdir="z", offset=float(np.min(Z)), cmap="viridis", levels=8, linewidths=0.8)
        idx_max = np.unravel_index(np.argmax(Z), Z.shape)
        idx_min = np.unravel_index(np.argmin(Z), Z.shape)
        ax.scatter([X[idx_max]], [Y[idx_max]], [Z[idx_max]], color="crimson", s=30)
        ax.scatter([X[idx_min]], [Y[idx_min]], [Z[idx_min]], color="navy", s=30)
        ax.text(X[idx_max], Y[idx_max], Z[idx_max], f" qmax={float(Z[idx_max]):.1f}", color="crimson")
        ax.text(X[idx_min], Y[idx_min], Z[idx_min], f" qmin={float(Z[idx_min]):.1f}", color="navy")
        self.fig_3d.colorbar(surf, ax=ax, shrink=0.6, pad=0.08, label="Presion (kPa)")
        ax.set_title("Superficie 3D de presiones de contacto")
        ax.set_xlabel("B (m)")
        ax.set_ylabel("L (m)")
        ax.set_zlabel("q (kPa)")
        ax.view_init(elev=24, azim=-50)
        self.fig_3d.tight_layout()
        self.canvas_3d.draw()

    # ======================================================
    # AUX
    # ======================================================
    def limpiar(self):
        self.modo.setCurrentIndex(0)
        self.norma.setCurrentIndex(0)
        self.tipo_zapata.setCurrentIndex(0)
        self.relacion.setText("1.00")
        self.qadm.setText("250")
        self.gamma_c.setText("24")
        self.fc.setText("28")
        self.fy.setText("420")
        self.n_serv.setText("900")
        self.mx_serv.setText("0")
        self.my_serv.setText("0")
        self.pu.setText("900")
        self.mux.setText("0")
        self.muy.setText("0")
        self.n2_serv.setText("700")
        self.n2_u.setText("700")
        self.sep_columnas.setText("3000")
        self.carga_lineal_serv.setText("300")
        self.carga_lineal_u.setText("300")
        self.c1.setText("400")
        self.c2.setText("400")
        self.c1b.setText("400")
        self.c2b.setText("400")
        self.b.setText("2000")
        self.l.setText("2000")
        self.h.setText("500")
        self.rec.setText("75")
        self.db.setText("16")
        self.ancho_corrida.setText("1200")
        self.n_barras_x.setText("10")
        self.db_x.setText("16")
        self.n_barras_y.setText("10")
        self.db_y.setText("16")
        self.texto_comp.clear()
        self.texto_armado.clear()
        self.texto_res.clear()
        self.fig_2d.clear()
        self.canvas_2d.draw()
        self.fig_3d.clear()
        self.canvas_3d.draw()
        self.ultimo_resultado = {}
        self._actualizar_tipo_zapata()

    def guardar(self):
        if not self.ultimo_resultado:
            QMessageBox.information(self, "Aviso", "Primero debes calcular.")
            return
        guardar_resultado("zapatas", self.ultimo_resultado)
        QMessageBox.information(self, "Guardado", "Resultados de zapatas guardados correctamente.")
