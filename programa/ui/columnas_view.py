import math
import numpy as np

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTextEdit, QGridLayout, QMessageBox, QGroupBox, QComboBox, QTabWidget,
    QSpinBox, QScrollArea, QSizePolicy, QFrame, QCheckBox
)

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

from data.storage import guardar_resultado, obtener_configuracion


class ColumnasView(QWidget):
    def __init__(self):
        super().__init__()

        self.ultimo_resultado = {}
        self.ultimo_grafico = {}
        self.ultimas_sugerencias_auto = []
        self.ultimo_diagnostico_auto = ""
        self._datos_modificados = False

        self.config = obtener_configuracion()

        self.unidad_fuerza = self.config.get("unidad_fuerza", "kN")
        self.unidad_momento = self.config.get("unidad_momento", "kN·m")
        self.unidad_longitud = self.config.get("unidad_longitud", "mm")
        self.unidad_recubrimiento = self.config.get("unidad_recubrimiento", "mm")
        self.unidad_diametro_barra = self.config.get("unidad_diametro_barra", "mm")
        self.unidad_area_acero = self.config.get("unidad_area_acero", "mm²")

        self.normas = {
            "ACI 318-19": {
                "rho_min_col": 0.01,
                "rho_max_col": 0.08,
                "phi_min": 0.65,
                "phi_max": 0.90,
                "eps_ty": 0.002,
                "eps_tension_controlled": 0.005,
                "clear_spacing_min_mm": 40.0,
                "min_rec_mm": 25.0,
                "min_total_barras": 4,
                "min_tie_diameter_mm": 6.0,
                "max_tie_spacing_rule_mm": 144.0,
                "nombre": "ACI 318-19",
            },
            "ACI 318-25": {
                "rho_min_col": 0.01,
                "rho_max_col": 0.08,
                "phi_min": 0.65,
                "phi_max": 0.90,
                "eps_ty": 0.002,
                "eps_tension_controlled": 0.005,
                "clear_spacing_min_mm": 40.0,
                "min_rec_mm": 25.0,
                "min_total_barras": 4,
                "min_tie_diameter_mm": 6.0,
                "max_tie_spacing_rule_mm": 144.0,
                "nombre": "ACI 318-25",
            },
            "NB 1225001-1:2017": {
                "rho_min_col": 0.006,
                "rho_max_col": 0.08,
                "phi_min": 0.65,
                "phi_max": 0.90,
                "eps_ty": 0.002,
                "eps_tension_controlled": 0.005,
                "clear_spacing_min_mm": 40.0,
                "min_rec_mm": 25.0,
                "min_total_barras": 4,
                "min_tie_diameter_mm": 6.0,
                "max_tie_spacing_rule_mm": 144.0,
                "nombre": "NB 1225001-1:2017",
            },
        }

        layout_principal = QVBoxLayout(self)

        titulo = QLabel("MÓDULO COLUMNAS - VERIFICACIÓN Y DISEÑO")
        titulo.setStyleSheet("font-size: 16px; font-weight: bold; padding: 4px;")
        layout_principal.addWidget(titulo)

        self.tabs = QTabWidget()
        layout_principal.addWidget(self.tabs)

        self.tab_datos = QWidget()
        self.tab_comprobaciones = QWidget()
        self.tab_resultados = QWidget()
        self.tab_diagrama = QWidget()
        self.tab_estribos = QWidget()

        self.tabs.addTab(self.tab_datos, "Datos")
        self.tabs.addTab(self.tab_comprobaciones, "Comprobaciones")
        self.tabs.addTab(self.tab_resultados, "Resultados")
        self.tabs.addTab(self.tab_diagrama, "Diagrama")
        self.tabs.addTab(self.tab_estribos, "Estribos")

        self._crear_tab_datos()
        self._crear_tab_comprobaciones()
        self._crear_tab_resultados()
        self._crear_tab_diagrama()
        self._crear_tab_estribos()

        self._actualizar_texto_unidades()
        self._actualizar_visibilidad_momentos()
        self._actualizar_modo_columna()
        self._conectar_actualizacion_croquis()
        self._conectar_entradas_recalculo()
        self._actualizar_croquis()

    # ======================================================
    # NORMAS
    # ======================================================
    def _norma_actual(self):
        return self.normas[self.combo_norma.currentText()]

    # ======================================================
    # CONVERSIONES
    # ======================================================
    def _longitud_a_mm(self, valor):
        if self.unidad_longitud == "mm":
            return valor
        if self.unidad_longitud == "cm":
            return valor * 10.0
        if self.unidad_longitud == "m":
            return valor * 1000.0
        return valor

    def _mm_a_longitud_usuario(self, valor_mm):
        if self.unidad_longitud == "mm":
            return valor_mm
        if self.unidad_longitud == "cm":
            return valor_mm / 10.0
        if self.unidad_longitud == "m":
            return valor_mm / 1000.0
        return valor_mm

    def _recubrimiento_a_mm(self, valor):
        if self.unidad_recubrimiento == "mm":
            return valor
        if self.unidad_recubrimiento == "cm":
            return valor * 10.0
        return valor

    def _diametro_a_mm(self, valor):
        if self.unidad_diametro_barra == "mm":
            return valor
        if self.unidad_diametro_barra == "cm":
            return valor * 10.0
        return valor

    def _mm_a_diametro_usuario(self, valor_mm):
        if self.unidad_diametro_barra == "mm":
            return valor_mm
        if self.unidad_diametro_barra == "cm":
            return valor_mm / 10.0
        return valor_mm

    def _factor_fuerza_a_kN(self):
        if self.unidad_fuerza == "kN":
            return 1.0
        if self.unidad_fuerza == "tf":
            return 9.80665
        if self.unidad_fuerza == "kgf":
            return 0.00980665
        return 1.0

    def _factor_momento_a_kNm(self):
        if self.unidad_momento == "kN·m":
            return 1.0
        if self.unidad_momento == "tf·m":
            return 9.80665
        if self.unidad_momento == "kgf·m":
            return 0.00980665
        return 1.0

    def _area_a_unidad_mostrada(self, area_mm2):
        if self.unidad_area_acero == "mm²":
            return area_mm2
        if self.unidad_area_acero == "cm²":
            return area_mm2 / 100.0
        return area_mm2

    def _valor_tentativo_longitud(self, valor_mm):
        return str(self._mm_a_longitud_usuario(valor_mm))

    def _valor_tentativo_recubrimiento(self, valor_mm):
        if self.unidad_recubrimiento == "mm":
            return str(valor_mm)
        if self.unidad_recubrimiento == "cm":
            return str(valor_mm / 10.0)
        return str(valor_mm)

    def _valor_tentativo_diametro(self, valor_mm):
        return str(self._mm_a_diametro_usuario(valor_mm))

    # ======================================================
    # UTILIDADES
    # ======================================================
    def _barras_combo_textos(self):
        if self.unidad_diametro_barra == "mm":
            return ["6", "8", "10", "12", "14", "16", "18", "20", "22", "25", "28", "32"]
        return ["0.6", "0.8", "1.0", "1.2", "1.4", "1.6", "1.8", "2.0", "2.2", "2.5", "2.8", "3.2"]

    def _set_combo_text_safe(self, combo, valor_mm):
        if self.unidad_diametro_barra == "cm":
            texto = f"{valor_mm / 10.0:.1f}"
        else:
            texto = f"{int(round(valor_mm))}"
        idx = combo.findText(texto)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    def _bar_area_mm2(self, d_mm):
        return math.pi * d_mm**2 / 4.0

    def _Ec_nb_mpa(self, fc):
        return 4700.0 * math.sqrt(fc)

    def _radio_giro(self, I, A):
        if A <= 0:
            return 0.0
        return math.sqrt(I / A)

    def _distancia_libre_entre_barras(self, p1, p2):
        dx = p2["x"] - p1["x"]
        dy = p2["y"] - p1["y"]
        dist_centros = math.sqrt(dx**2 + dy**2)
        return dist_centros - (p1["diametro"] + p2["diametro"]) / 2.0

    # ======================================================
    # TAB DATOS
    # ======================================================
    def _crear_tab_datos(self):
        layout_externo = QVBoxLayout(self.tab_datos)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        layout_externo.addWidget(scroll)

        contenido = QWidget()
        scroll.setWidget(contenido)
        layout = QVBoxLayout(contenido)

        grupo_tipo = QGroupBox("1. Tipo de comprobación")
        layout_tipo = QGridLayout()

        self.tipo_calculo = QComboBox()
        self.tipo_calculo.addItems(["Compresión simple", "Compresión compuesta"])
        self.tipo_calculo.currentIndexChanged.connect(self._actualizar_visibilidad_momentos)

        self.modo_columna = QComboBox()
        self.modo_columna.addItems([
            "Verificación con acero definido",
            "Diseño automático de acero"
        ])
        self.modo_columna.currentIndexChanged.connect(self._actualizar_modo_columna)

        self.combo_norma = QComboBox()
        self.combo_norma.addItems(list(self.normas.keys()))
        self.combo_norma.currentIndexChanged.connect(self._actualizar_texto_unidades)

        layout_tipo.addWidget(QLabel("Tipo de revisión"), 0, 0)
        layout_tipo.addWidget(self.tipo_calculo, 0, 1)
        layout_tipo.addWidget(QLabel("Modo de trabajo"), 1, 0)
        layout_tipo.addWidget(self.modo_columna, 1, 1)
        layout_tipo.addWidget(QLabel("Norma"), 2, 0)
        layout_tipo.addWidget(self.combo_norma, 2, 1)

        grupo_tipo.setLayout(layout_tipo)
        layout.addWidget(grupo_tipo)

        grupo_unidades = QGroupBox("2. Sistema de unidades activo")
        layout_unidades = QVBoxLayout()
        self.lbl_unidades = QLabel()
        self.lbl_unidades.setWordWrap(True)
        layout_unidades.addWidget(self.lbl_unidades)
        grupo_unidades.setLayout(layout_unidades)
        layout.addWidget(grupo_unidades)

        grupo_geom = QGroupBox("3. Geometría y materiales")
        layout_geom = QGridLayout()

        self.b = QLineEdit(self._valor_tentativo_longitud(300))
        self.h = QLineEdit(self._valor_tentativo_longitud(400))
        self.fc = QLineEdit("28")
        self.fy = QLineEdit("420")
        self.dst = QLineEdit(self._valor_tentativo_diametro(8))

        layout_geom.addWidget(QLabel(f"b ({self.unidad_longitud})"), 0, 0)
        layout_geom.addWidget(self.b, 0, 1)
        layout_geom.addWidget(QLabel(f"h ({self.unidad_longitud})"), 1, 0)
        layout_geom.addWidget(self.h, 1, 1)
        layout_geom.addWidget(QLabel("f'c (MPa)"), 2, 0)
        layout_geom.addWidget(self.fc, 2, 1)
        layout_geom.addWidget(QLabel("fy (MPa)"), 3, 0)
        layout_geom.addWidget(self.fy, 3, 1)
        layout_geom.addWidget(QLabel(f"Diámetro del estribo ({self.unidad_diametro_barra})"), 4, 0)
        layout_geom.addWidget(self.dst, 4, 1)

        grupo_geom.setLayout(layout_geom)
        layout.addWidget(grupo_geom)

        fila_acero_croquis = QHBoxLayout()

        grupo_acero = QGroupBox("4. Armado longitudinal")
        layout_acero = QGridLayout()

        layout_acero.addWidget(QLabel("Concepto"), 0, 0)
        layout_acero.addWidget(QLabel("Cantidad"), 0, 1)
        layout_acero.addWidget(QLabel(f"Diámetro ({self.unidad_diametro_barra})"), 0, 2)

        self.n_esquinas_info = QLabel("4")
        self.db_esquinas = QComboBox()
        self.n_cara_x = QSpinBox()
        self.n_cara_y = QSpinBox()
        self.db_cara_x = QComboBox()
        self.db_cara_y = QComboBox()

        self.n_cara_x.setRange(0, 20)
        self.n_cara_y.setRange(0, 20)
        self.n_cara_x.setValue(2)
        self.n_cara_y.setValue(2)

        for cb in [self.db_esquinas, self.db_cara_x, self.db_cara_y]:
            cb.addItems(self._barras_combo_textos())
            cb.setCurrentText(self._valor_tentativo_diametro(12))

        layout_acero.addWidget(QLabel("Esquinas"), 1, 0)
        layout_acero.addWidget(self.n_esquinas_info, 1, 1)
        layout_acero.addWidget(self.db_esquinas, 1, 2)

        layout_acero.addWidget(QLabel("Cara X (por cara)"), 2, 0)
        layout_acero.addWidget(self.n_cara_x, 2, 1)
        layout_acero.addWidget(self.db_cara_x, 2, 2)

        layout_acero.addWidget(QLabel("Cara Y (por cara)"), 3, 0)
        layout_acero.addWidget(self.n_cara_y, 3, 1)
        layout_acero.addWidget(self.db_cara_y, 3, 2)

        self.c_x = QLineEdit(self._valor_tentativo_recubrimiento(30))
        self.c_y = QLineEdit(self._valor_tentativo_recubrimiento(30))

        layout_acero.addWidget(QLabel(f"Recubrimiento libre X ({self.unidad_recubrimiento})"), 4, 0)
        layout_acero.addWidget(self.c_x, 4, 1, 1, 2)
        layout_acero.addWidget(QLabel(f"Recubrimiento libre Y ({self.unidad_recubrimiento})"), 5, 0)
        layout_acero.addWidget(self.c_y, 5, 1, 1, 2)

        self.btn_actualizar_croquis = QPushButton("Actualizar croquis")
        layout_acero.addWidget(self.btn_actualizar_croquis, 6, 0, 1, 3)

        self.lbl_armado_auto = QLabel("Armado adoptado: pendiente de calcular")
        self.lbl_armado_auto.setWordWrap(True)
        self.lbl_armado_auto.setStyleSheet("padding: 6px; border: 1px solid gray;")
        layout_acero.addWidget(self.lbl_armado_auto, 7, 0, 1, 3)

        grupo_acero.setLayout(layout_acero)
        fila_acero_croquis.addWidget(grupo_acero, 3)

        grupo_croquis = QGroupBox("Croquis de la sección")
        layout_croquis = QVBoxLayout()
        self.figure_sec = Figure(figsize=(4.8, 4.2))
        self.canvas_sec = FigureCanvas(self.figure_sec)
        self.canvas_sec.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout_croquis.addWidget(self.canvas_sec)
        grupo_croquis.setLayout(layout_croquis)
        fila_acero_croquis.addWidget(grupo_croquis, 2)

        layout.addLayout(fila_acero_croquis)

        grupo_diseno = QGroupBox("5. Diseño automático de acero")
        layout_diseno = QGridLayout()

        self.combo_barras_diseno = QComboBox()
        self.combo_barras_diseno.addItems([
            "12,16,20,25",
            "12,16,20,25,32",
            "16,20,25,32",
            "12,14,16,18,20,22,25,32",
        ])

        self.nmin_total = QSpinBox()
        self.nmin_total.setRange(4, 40)
        self.nmin_total.setSingleStep(2)
        self.nmin_total.setValue(8)

        self.nmax_total = QSpinBox()
        self.nmax_total.setRange(4, 60)
        self.nmax_total.setSingleStep(2)
        self.nmax_total.setValue(16)

        layout_diseno.addWidget(QLabel("Diámetros disponibles (mm)"), 0, 0)
        layout_diseno.addWidget(self.combo_barras_diseno, 0, 1)
        layout_diseno.addWidget(QLabel("Total mínimo de barras"), 1, 0)
        layout_diseno.addWidget(self.nmin_total, 1, 1)
        layout_diseno.addWidget(QLabel("Total máximo de barras"), 2, 0)
        layout_diseno.addWidget(self.nmax_total, 2, 1)

        grupo_diseno.setLayout(layout_diseno)
        layout.addWidget(grupo_diseno)
        self.grupo_diseno = grupo_diseno

        grupo_cargas = QGroupBox("6. Cargas actuantes")
        layout_cargas = QGridLayout()

        self.lbl_pu = QLabel(f"Pu ({self.unidad_fuerza})")
        self.lbl_mux = QLabel(f"Mux ({self.unidad_momento})")
        self.lbl_muy = QLabel(f"Muy ({self.unidad_momento})")

        self.pu = QLineEdit("147")
        self.mux = QLineEdit("3.48")
        self.muy = QLineEdit("0.26")

        layout_cargas.addWidget(self.lbl_pu, 0, 0)
        layout_cargas.addWidget(self.pu, 0, 1)
        layout_cargas.addWidget(self.lbl_mux, 1, 0)
        layout_cargas.addWidget(self.mux, 1, 1)
        layout_cargas.addWidget(self.lbl_muy, 2, 0)
        layout_cargas.addWidget(self.muy, 2, 1)

        grupo_cargas.setLayout(layout_cargas)
        layout.addWidget(grupo_cargas)
        self.grupo_cargas = grupo_cargas

        grupo_esb = QGroupBox("7. Esbeltez y factor k")
        layout_esb = QGridLayout()

        self.lu_x = QLineEdit(self._valor_tentativo_longitud(3000))
        self.lu_y = QLineEdit(self._valor_tentativo_longitud(3000))
        self.k_x = QLineEdit("1.00")
        self.k_y = QLineEdit("1.00")
        self.e_min = QLineEdit(self._valor_tentativo_longitud(20))
        self.usar_rigidez_efectiva = QCheckBox("Usar factor de rigidez efectiva (opcional)")
        self.factor_rigidez_efectiva = QLineEdit("0.15")
        self.factor_rigidez_efectiva.setEnabled(False)
        self.usar_rigidez_efectiva.toggled.connect(self.factor_rigidez_efectiva.setEnabled)

        layout_esb.addWidget(QLabel(f"Longitud libre lu_x ({self.unidad_longitud})"), 0, 0)
        layout_esb.addWidget(self.lu_x, 0, 1)
        layout_esb.addWidget(QLabel(f"Longitud libre lu_y ({self.unidad_longitud})"), 1, 0)
        layout_esb.addWidget(self.lu_y, 1, 1)
        layout_esb.addWidget(QLabel("Factor k_x"), 2, 0)
        layout_esb.addWidget(self.k_x, 2, 1)
        layout_esb.addWidget(QLabel("Factor k_y"), 3, 0)
        layout_esb.addWidget(self.k_y, 3, 1)
        layout_esb.addWidget(QLabel(f"Excentricidad mínima adoptada ({self.unidad_longitud})"), 4, 0)
        layout_esb.addWidget(self.e_min, 4, 1)
        layout_esb.addWidget(self.usar_rigidez_efectiva, 5, 0, 1, 2)
        layout_esb.addWidget(QLabel("Factor de rigidez efectiva"), 6, 0)
        layout_esb.addWidget(self.factor_rigidez_efectiva, 6, 1)

        grupo_esb.setLayout(layout_esb)
        layout.addWidget(grupo_esb)

        grupo_psi = QGroupBox("8. Ayuda para estimar k con ψA y ψB")
        layout_psi = QGridLayout()

        self.psiA_col = QLineEdit("8000000")
        self.psiA_vig = QLineEdit("6000000")
        self.psiB_col = QLineEdit("8000000")
        self.psiB_vig = QLineEdit("6000000")

        layout_psi.addWidget(QLabel("Nudo A - Σ(I/L) columnas"), 0, 0)
        layout_psi.addWidget(self.psiA_col, 0, 1)
        layout_psi.addWidget(QLabel("Nudo A - Σ(I/L) vigas"), 1, 0)
        layout_psi.addWidget(self.psiA_vig, 1, 1)
        layout_psi.addWidget(QLabel("Nudo B - Σ(I/L) columnas"), 2, 0)
        layout_psi.addWidget(self.psiB_col, 2, 1)
        layout_psi.addWidget(QLabel("Nudo B - Σ(I/L) vigas"), 3, 0)
        layout_psi.addWidget(self.psiB_vig, 3, 1)

        self.btn_estimar_k = QPushButton("Estimar k automáticamente")
        self.btn_estimar_k.clicked.connect(self._estimar_k_desde_psi)
        layout_psi.addWidget(self.btn_estimar_k, 4, 0, 1, 2)

        self.lbl_psi_resultado = QLabel("ψA = -, ψB = -, k estimado = -")
        self.lbl_psi_resultado.setStyleSheet("font-weight: bold;")
        layout_psi.addWidget(self.lbl_psi_resultado, 5, 0, 1, 2)

        grupo_psi.setLayout(layout_psi)
        layout.addWidget(grupo_psi)

        grupo_est = QGroupBox("9. Estribos / cortante")
        layout_est = QGridLayout()

        self.vx_col = QLineEdit("0.04")
        self.vy_col = QLineEdit("0.84")
        self.fy_estribo = QLineEdit("420")

        self.num_ramas_x = QSpinBox()
        self.num_ramas_x.setRange(2, 8)
        self.num_ramas_x.setValue(2)

        self.num_ramas_y = QSpinBox()
        self.num_ramas_y.setRange(2, 8)
        self.num_ramas_y.setValue(2)

        self.db_estribo_combo = QComboBox()
        self.db_estribo_combo.addItems(self._barras_combo_textos())
        self.db_estribo_combo.setCurrentText(self._valor_tentativo_diametro(8))

        self.sep_estribo_adoptada = QLineEdit(self._valor_tentativo_longitud(140))
        self.altura_estribada = QLineEdit(self._valor_tentativo_longitud(3000))
        self.recubrimiento_estribo = QLineEdit(self._valor_tentativo_recubrimiento(30))

        layout_est.addWidget(QLabel(f"Vx ({self.unidad_fuerza})"), 0, 0)
        layout_est.addWidget(self.vx_col, 0, 1)
        layout_est.addWidget(QLabel(f"Vy ({self.unidad_fuerza})"), 1, 0)
        layout_est.addWidget(self.vy_col, 1, 1)
        layout_est.addWidget(QLabel("fy estribo (MPa)"), 2, 0)
        layout_est.addWidget(self.fy_estribo, 2, 1)
        layout_est.addWidget(QLabel("Ramas en X"), 3, 0)
        layout_est.addWidget(self.num_ramas_x, 3, 1)
        layout_est.addWidget(QLabel("Ramas en Y"), 4, 0)
        layout_est.addWidget(self.num_ramas_y, 4, 1)
        layout_est.addWidget(QLabel(f"Diámetro estribo ({self.unidad_diametro_barra})"), 5, 0)
        layout_est.addWidget(self.db_estribo_combo, 5, 1)
        layout_est.addWidget(QLabel(f"Separación adoptada ({self.unidad_longitud})"), 6, 0)
        layout_est.addWidget(self.sep_estribo_adoptada, 6, 1)
        layout_est.addWidget(QLabel(f"Altura a estribar ({self.unidad_longitud})"), 7, 0)
        layout_est.addWidget(self.altura_estribada, 7, 1)
        layout_est.addWidget(QLabel(f"Recubrimiento estribo ({self.unidad_recubrimiento})"), 8, 0)
        layout_est.addWidget(self.recubrimiento_estribo, 8, 1)

        self.btn_calc_estribos = QPushButton("Calcular / verificar estribos")
        self.btn_calc_estribos.clicked.connect(self.calcular_estribos)
        layout_est.addWidget(self.btn_calc_estribos, 9, 0, 1, 2)

        grupo_est.setLayout(layout_est)
        layout.addWidget(grupo_est)
        self.grupo_estribos_datos = grupo_est

        fila_botones = QHBoxLayout()
        self.btn_calcular = QPushButton("Calcular")
        self.btn_limpiar = QPushButton("Limpiar")
        self.btn_guardar = QPushButton("Guardar resultados")

        self.btn_calcular.clicked.connect(self.calcular)
        self.btn_limpiar.clicked.connect(self.limpiar)
        self.btn_guardar.clicked.connect(self.guardar)

        fila_botones.addWidget(self.btn_calcular)
        fila_botones.addWidget(self.btn_limpiar)
        fila_botones.addWidget(self.btn_guardar)
        layout.addLayout(fila_botones)

        self.lbl_dirty = QLabel("")
        self.lbl_dirty.setStyleSheet("color: #b36b00; font-weight: bold; padding: 4px;")
        layout.addWidget(self.lbl_dirty)

        layout.addStretch()

    # ======================================================
    # TABS RESTANTES
    # ======================================================
    def _crear_tab_comprobaciones(self):
        layout = QVBoxLayout(self.tab_comprobaciones)
        self.texto_comprobaciones = QTextEdit()
        self.texto_comprobaciones.setReadOnly(True)
        layout.addWidget(self.texto_comprobaciones)

    def _crear_tab_resultados(self):
        layout = QVBoxLayout(self.tab_resultados)
        self.resultados_texto = QTextEdit()
        self.resultados_texto.setReadOnly(True)
        layout.addWidget(self.resultados_texto)

    def _crear_tab_diagrama(self):
        layout = QVBoxLayout(self.tab_diagrama)

        self.lbl_guia_diagrama = QLabel(
            "• 2D - Eje X: P-Mx\n"
            "• 2D - Eje Y: P-My\n"
            "• 2D - Comparación tipo Excel\n"
            "• 3D - Superficie aproximada P-Mx-My"
        )
        self.lbl_guia_diagrama.setWordWrap(True)
        self.lbl_guia_diagrama.setFrameShape(QFrame.StyledPanel)
        self.lbl_guia_diagrama.setStyleSheet("padding: 8px;")
        layout.addWidget(self.lbl_guia_diagrama)

        fila_selector = QHBoxLayout()
        fila_selector.addWidget(QLabel("Vista del diagrama"))

        self.combo_vista_diagrama = QComboBox()
        self.combo_vista_diagrama.addItems([
            "2D - Eje X",
            "2D - Eje Y",
            "2D - Comparación tipo Excel",
            "3D - Superficie de interacción"
        ])
        self.combo_vista_diagrama.currentIndexChanged.connect(self._redibujar_ultimo_grafico)
        fila_selector.addWidget(self.combo_vista_diagrama)

        layout.addLayout(fila_selector)

        self.figure = Figure(figsize=(8.5, 6.5))
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

    def _crear_tab_estribos(self):
        layout = QVBoxLayout(self.tab_estribos)
        self.texto_estribos = QTextEdit()
        self.texto_estribos.setReadOnly(True)
        layout.addWidget(self.texto_estribos)

    # ======================================================
    # RECALCULO
    # ======================================================
    def _conectar_entradas_recalculo(self):
        widgets_lineedit = [
            self.b, self.h, self.fc, self.fy, self.dst,
            self.c_x, self.c_y,
            self.pu, self.mux, self.muy,
            self.lu_x, self.lu_y, self.k_x, self.k_y, self.e_min,
            self.factor_rigidez_efectiva,
            self.psiA_col, self.psiA_vig, self.psiB_col, self.psiB_vig,
            self.vx_col, self.vy_col, self.fy_estribo,
            self.sep_estribo_adoptada, self.altura_estribada, self.recubrimiento_estribo
        ]

        widgets_combo = [
            self.combo_norma, self.tipo_calculo, self.modo_columna,
            self.db_esquinas, self.db_cara_x, self.db_cara_y,
            self.combo_barras_diseno, self.db_estribo_combo
        ]

        widgets_spin = [
            self.n_cara_x, self.n_cara_y,
            self.nmin_total, self.nmax_total,
            self.num_ramas_x, self.num_ramas_y
        ]

        self.usar_rigidez_efectiva.toggled.connect(self._marcar_resultados_como_desactualizados)

        for w in widgets_lineedit:
            w.textChanged.connect(self._marcar_resultados_como_desactualizados)

        for w in widgets_combo:
            w.currentTextChanged.connect(self._marcar_resultados_como_desactualizados)

        for w in widgets_spin:
            w.valueChanged.connect(self._marcar_resultados_como_desactualizados)

    def _marcar_resultados_como_desactualizados(self, *args):
        self._datos_modificados = True
        if hasattr(self, "lbl_dirty"):
            self.lbl_dirty.setText("⚠️ Cambiaste datos. Presiona Calcular para actualizar resultados.")

    def _limpiar_salidas_previas(self):
        self.ultimo_resultado = {}
        self.ultimo_grafico = {}
        self.ultimas_sugerencias_auto = []
        self.ultimo_diagnostico_auto = ""

        if hasattr(self, "resultados_texto"):
            self.resultados_texto.clear()
        if hasattr(self, "texto_comprobaciones"):
            self.texto_comprobaciones.clear()
        if hasattr(self, "texto_estribos"):
            self.texto_estribos.clear()

    # ======================================================
    # INTERFAZ
    # ======================================================
    def _actualizar_visibilidad_momentos(self):
        es_diseno = self.modo_columna.currentText() == "Diseño automático de acero"
        es_simple = self.tipo_calculo.currentText() == "Compresión simple"
        mostrar_momentos = es_diseno and not es_simple

        self.lbl_mux.setVisible(es_diseno)
        self.lbl_muy.setVisible(es_diseno)
        self.mux.setVisible(es_diseno)
        self.muy.setVisible(es_diseno)
        self.mux.setEnabled(mostrar_momentos)
        self.muy.setEnabled(mostrar_momentos)

        if not mostrar_momentos:
            self.mux.setText("0")
            self.muy.setText("0")

    def _actualizar_modo_columna(self):
        es_diseno = self.modo_columna.currentText() == "Diseño automático de acero"
        self.grupo_diseno.setVisible(es_diseno)
        self.grupo_cargas.setVisible(True)
        self.grupo_estribos_datos.setVisible(es_diseno)
        self.lbl_pu.setVisible(True)
        self.pu.setVisible(True)

        self.n_cara_x.setEnabled(not es_diseno)
        self.n_cara_y.setEnabled(not es_diseno)
        self.db_esquinas.setEnabled(not es_diseno)
        self.db_cara_x.setEnabled(not es_diseno)
        self.db_cara_y.setEnabled(not es_diseno)

        idx_tab_estribos = self.tabs.indexOf(self.tab_estribos)
        if idx_tab_estribos >= 0 and hasattr(self.tabs, "setTabVisible"):
            self.tabs.setTabVisible(idx_tab_estribos, es_diseno)

        if not es_diseno:
            self.mux.setText("0")
            self.muy.setText("0")
            self.vx_col.setText("0")
            self.vy_col.setText("0")
            if self.tabs.currentWidget() == self.tab_estribos:
                self.tabs.setCurrentWidget(self.tab_datos)
            self.grupo_cargas.setTitle("6. Carga axial de referencia")
        else:
            self.grupo_cargas.setTitle("6. Cargas actuantes")

        self._actualizar_visibilidad_momentos()

        if es_diseno:
            self.lbl_armado_auto.setText(
                "Armado automático adoptado: pendiente de calcular.\n"
                "Si no encuentra solución, el programa te sugerirá qué conviene cambiar."
            )
        else:
            self.lbl_armado_auto.setText(
                "Modo manual: define el armado por esquinas, Cara X y Cara Y."
            )

    def _actualizar_texto_unidades(self):
        norma = self._norma_actual()
        self.lbl_unidades.setText(
            f"Norma activa: {norma['nombre']}\n"
            f"Geometría de sección: {self.unidad_longitud}\n"
            f"Recubrimientos: {self.unidad_recubrimiento}\n"
            f"Diámetros de barras y estribos: {self.unidad_diametro_barra}\n"
            f"Carga axial y cortante: {self.unidad_fuerza}\n"
            f"Momentos: {self.unidad_momento}\n"
            f"Área de acero mostrada: {self.unidad_area_acero}\n"
            "Base interna del cálculo: mm, MPa, kN, kN·m"
        )

    def _conectar_actualizacion_croquis(self):
        self.btn_actualizar_croquis.clicked.connect(self._actualizar_croquis)
        self.n_cara_x.valueChanged.connect(self._actualizar_croquis)
        self.n_cara_y.valueChanged.connect(self._actualizar_croquis)

        for combo in [self.db_esquinas, self.db_cara_x, self.db_cara_y]:
            combo.currentTextChanged.connect(self._actualizar_croquis)

        for line in [self.b, self.h, self.dst, self.c_x, self.c_y]:
            line.textChanged.connect(self._actualizar_croquis)

    def _calcular_psi(self, suma_col, suma_vig):
        if suma_vig <= 0:
            return None
        return suma_col / suma_vig

    def _estimar_k_desde_psi(self):
        try:
            a_col = float(self.psiA_col.text())
            a_vig = float(self.psiA_vig.text())
            b_col = float(self.psiB_col.text())
            b_vig = float(self.psiB_vig.text())

            psi_a = self._calcular_psi(a_col, a_vig)
            psi_b = self._calcular_psi(b_col, b_vig)

            if psi_a is None or psi_b is None:
                raise ValueError("Las sumas de vigas deben ser mayores que cero.")

            k_est = 0.7 + 0.05 * (psi_a + psi_b)
            k_est = max(0.65, min(1.0, k_est))

            self.k_x.setText(f"{k_est:.3f}")
            self.k_y.setText(f"{k_est:.3f}")
            self.lbl_psi_resultado.setText(
                f"ψA = {psi_a:.3f}, ψB = {psi_b:.3f}, k estimado = {k_est:.3f}"
            )

        except Exception as e:
            QMessageBox.warning(self, "Error en ψ", f"Revisa los datos ingresados.\n\n{e}")

    # ======================================================
    # ARMADO
    # ======================================================
    def _contar_barras(self, barras):
        return len(barras)

    def _total_barras_actual(self):
        return 4 + 2 * self.n_cara_x.value() + 2 * self.n_cara_y.value()

    def _actualizar_resumen_armado(self, area_mostrada=None, rho=None, extra=""):
        texto = (
            "ARMADO ADOPTADO\n"
            f"Esquinas: 4 Ø{self.db_esquinas.currentText()}\n"
            f"Cara X: {self.n_cara_x.value()} por cara Ø{self.db_cara_x.currentText()}\n"
            f"Cara Y: {self.n_cara_y.value()} por cara Ø{self.db_cara_y.currentText()}\n"
            f"Total de barras: {self._total_barras_actual()}"
        )
        if area_mostrada is not None:
            texto += f"\nAs total: {area_mostrada:.2f} {self.unidad_area_acero}"
        if rho is not None:
            texto += f"\nCuantía ρ: {rho:.5f}"
        if extra:
            texto += f"\n{extra}"
        self.lbl_armado_auto.setText(texto)

    def _generar_barras_reales(self, b, h, d_st, n_cx, n_cy, d_esq, d_x, d_y):
        c_x = self._recubrimiento_a_mm(float(self.c_x.text()))
        c_y = self._recubrimiento_a_mm(float(self.c_y.text()))

        x0 = c_x + d_st + d_esq / 2.0
        x1 = b - (c_x + d_st + d_esq / 2.0)
        y0 = c_y + d_st + d_esq / 2.0
        y1 = h - (c_y + d_st + d_esq / 2.0)

        if x1 <= x0 or y1 <= y0:
            raise ValueError("Los recubrimientos y diámetros no caben dentro de la sección.")

        barras = []

        area_esq = self._bar_area_mm2(d_esq)
        esquinas = [(x0, y0), (x1, y0), (x0, y1), (x1, y1)]
        for x, y in esquinas:
            barras.append({"x": x, "y": y, "area": area_esq, "diametro": d_esq, "tipo": "esquina"})

        if n_cx > 0:
            xs = np.linspace(x0, x1, n_cx + 2)[1:-1]
            area_x = self._bar_area_mm2(d_x)
            for x in xs:
                barras.append({"x": float(x), "y": y0, "area": area_x, "diametro": d_x, "tipo": "cara_x"})
                barras.append({"x": float(x), "y": y1, "area": area_x, "diametro": d_x, "tipo": "cara_x"})

        if n_cy > 0:
            ys = np.linspace(y0, y1, n_cy + 2)[1:-1]
            area_y = self._bar_area_mm2(d_y)
            for y in ys:
                barras.append({"x": x0, "y": float(y), "area": area_y, "diametro": d_y, "tipo": "cara_y"})
                barras.append({"x": x1, "y": float(y), "area": area_y, "diametro": d_y, "tipo": "cara_y"})

        return barras

    def _generar_barras_desde_ui(self, b, h, d_st):
        d_esq = self._diametro_a_mm(float(self.db_esquinas.currentText()))
        d_x = self._diametro_a_mm(float(self.db_cara_x.currentText()))
        d_y = self._diametro_a_mm(float(self.db_cara_y.currentText()))

        return self._generar_barras_reales(
            b=b, h=h, d_st=d_st,
            n_cx=self.n_cara_x.value(),
            n_cy=self.n_cara_y.value(),
            d_esq=d_esq, d_x=d_x, d_y=d_y
        )

    def _aplicar_solucion_diseno(self, solucion):
        self.n_cara_x.setValue(solucion["n_cx"])
        self.n_cara_y.setValue(solucion["n_cy"])
        self._set_combo_text_safe(self.db_esquinas, solucion["d_esq_mm"])
        self._set_combo_text_safe(self.db_cara_x, solucion["d_x_mm"])
        self._set_combo_text_safe(self.db_cara_y, solucion["d_y_mm"])
        self._actualizar_croquis()

    def _lista_barras_disponibles(self):
        return [float(x.strip()) for x in self.combo_barras_diseno.currentText().split(",") if x.strip()]

    # ======================================================
    # CROQUIS
    # ======================================================
    def _actualizar_croquis(self):
        try:
            b = self._longitud_a_mm(float(self.b.text()))
            h = self._longitud_a_mm(float(self.h.text()))
            d_st = self._diametro_a_mm(float(self.dst.text()))

            barras = self._generar_barras_desde_ui(b, h, d_st)

            self.figure_sec.clear()
            ax = self.figure_sec.add_subplot(111)

            ax.plot([0, b, b, 0, 0], [0, 0, h, h, 0], linewidth=1.5)

            for bar in barras:
                ax.scatter(bar["x"], h - bar["y"], s=40)

            ax.set_title("Sección")
            ax.set_aspect("equal", adjustable="box")
            ax.set_xlim(-0.15 * b, 1.15 * b)
            ax.set_ylim(-0.15 * h, 1.15 * h)
            ax.grid(True)
            ax.set_xlabel("x (mm)")
            ax.set_ylabel("y (mm)")
            self.canvas_sec.draw()

        except Exception:
            pass

    # ======================================================
    # DIAGRAMA / CAPACIDAD
    # ======================================================
    def _beta1(self, fc_mpa):
        if fc_mpa <= 28:
            return 0.85
        beta1 = 0.85 - 0.05 * ((fc_mpa - 28) / 7.0)
        return max(0.65, beta1)

    def _phi(self, eps_t):
        norma = self._norma_actual()
        if eps_t <= norma["eps_ty"]:
            return norma["phi_min"]
        if eps_t >= norma["eps_tension_controlled"]:
            return norma["phi_max"]
        return norma["phi_min"] + (
            (eps_t - norma["eps_ty"]) *
            (norma["phi_max"] - norma["phi_min"]) /
            (norma["eps_tension_controlled"] - norma["eps_ty"])
        )

    def _frontera_interaccion(self, puntos_raw):
        if not puntos_raw:
            return []

        puntos = sorted(puntos_raw, key=lambda t: t[0])
        agrupados = {}
        for pto in puntos:
            m = float(pto[0])
            p = float(pto[1])
            resto = pto[2:]
            key = round(m, 3)
            if key not in agrupados or p > agrupados[key][1]:
                agrupados[key] = (m, p, *resto)

        puntos = list(agrupados.values())
        puntos.sort(key=lambda t: t[0])

        curva = []
        p_env = float("inf")
        for pto in puntos:
            m = float(pto[0])
            p = float(pto[1])
            resto = pto[2:]
            p_env = min(p_env, p)
            curva.append((m, p_env, *resto))

        if len(curva) >= 4:
            m_vals = np.array([c[0] for c in curva], dtype=float)
            p_vals = np.array([c[1] for c in curva], dtype=float)
            m_dense = np.linspace(m_vals.min(), m_vals.max(), 220)
            p_dense = np.interp(m_dense, m_vals, p_vals)

            if len(curva[0]) >= 3:
                e_vals = np.array([c[2] for c in curva], dtype=float)
                e_dense = np.interp(m_dense, m_vals, e_vals)
                return [(float(m), float(p), float(e)) for m, p, e in zip(m_dense, p_dense, e_dense)]

            return [(float(m), float(p)) for m, p in zip(m_dense, p_dense)]

        return curva

    def _diagrama_interaccion_uniaxial(self, b, h, fc, fy, barras, eje="X"):
        Es = 200000.0
        beta1 = self._beta1(fc)

        if eje == "X":
            width = b
            depth = h
            coords = [bar["y"] for bar in barras]
            areas = [bar["area"] for bar in barras]
        else:
            width = h
            depth = b
            coords = [bar["x"] for bar in barras]
            areas = [bar["area"] for bar in barras]

        puntos_raw = []
        c_values = np.linspace(5.0, depth * 3.0, 260)

        for c in c_values:
            a = min(beta1 * c, depth)
            Cc = 0.85 * fc * width * a
            y_cc = a / 2.0

            Pn = Cc
            Mn = Cc * (y_cc - depth / 2.0)

            eps_list = []
            for d_i, area_i in zip(coords, areas):
                eps_i = 0.003 * (1.0 - d_i / c)
                fs_i = max(-fy, min(fy, Es * eps_i))
                Fs_i = fs_i * area_i
                Pn += Fs_i
                Mn += Fs_i * (d_i - depth / 2.0)
                eps_list.append(eps_i)

            eps_t = max(0.0, -min(eps_list))
            phi = self._phi(eps_t)

            phiPn = phi * Pn / 1000.0
            phiMn = phi * abs(Mn) / 1e6

            if phiPn >= 0 and phiMn >= 0:
                puntos_raw.append((phiMn, phiPn, eps_t))

        Ag = b * h
        As_total = sum(bar["area"] for bar in barras)
        Po = 0.85 * fc * (Ag - As_total) + fy * As_total
        phiPo = self._norma_actual()["phi_min"] * 0.80 * Po / 1000.0

        puntos_raw.append((0.0, phiPo, 0.0))

        eps_y = fy / 200000.0
        punto_balanceado = min(puntos_raw, key=lambda x: abs(x[2] - eps_y))
        punto_comp_pura = (0.0, phiPo, 0.0)

        curva_limpia = self._frontera_interaccion(puntos_raw)
        punto_flexion = min(curva_limpia, key=lambda x: x[1]) if curva_limpia else None

        return curva_limpia, punto_comp_pura, punto_balanceado, punto_flexion, Po / 1000.0

    def _capacidad_momento_para_pu(self, curva, pu):
        if not curva:
            return None

        pares = [(m, p) for m, p, *_ in curva]
        pares = sorted(pares, key=lambda t: t[1])

        m_vals = np.array([m for m, _ in pares], dtype=float)
        p_vals = np.array([p for _, p in pares], dtype=float)

        if pu < np.min(p_vals) or pu > np.max(p_vals):
            return None

        return float(np.interp(pu, p_vals, m_vals))

    def _superficie_interaccion_3d(self, curva_x, curva_y):
        if not curva_x or not curva_y:
            return None

        px = np.array([p[1] for p in curva_x], dtype=float)
        mx = np.array([p[0] for p in curva_x], dtype=float)
        py = np.array([p[1] for p in curva_y], dtype=float)
        my = np.array([p[0] for p in curva_y], dtype=float)

        p_min = max(px.min(), py.min())
        p_max = min(px.max(), py.max())
        if p_max <= p_min:
            return None

        p_levels = np.linspace(p_min, p_max, 28)
        theta = np.linspace(0, 2 * np.pi, 80)

        X = np.zeros((len(p_levels), len(theta)))
        Y = np.zeros((len(p_levels), len(theta)))
        Z = np.zeros((len(p_levels), len(theta)))

        for i, p in enumerate(p_levels):
            cap_x = float(np.interp(p, np.sort(px), mx[np.argsort(px)]))
            cap_y = float(np.interp(p, np.sort(py), my[np.argsort(py)]))
            for j, t in enumerate(theta):
                denom = math.sqrt(
                    (math.cos(t) / max(cap_x, 1e-9)) ** 2 +
                    (math.sin(t) / max(cap_y, 1e-9)) ** 2
                )
                r = 1.0 / max(denom, 1e-9)
                X[i, j] = r * math.cos(t)
                Y[i, j] = r * math.sin(t)
                Z[i, j] = p

        return X, Y, Z

    # ======================================================
    # COMPROBACIONES
    # ======================================================
    def _check_disposicion_armaduras(self, b, h, barras, d_st, s_estribo_adoptada_mm):
        norma = self._norma_actual()
        min_sep = norma["clear_spacing_min_mm"]
        min_db_tie = norma["min_tie_diameter_mm"]
        s_max = norma["max_tie_spacing_rule_mm"]

        errores = []
        lineas = []
        lineas.append("1. DISPOSICIONES RELATIVAS A LAS ARMADURAS")

        min_libre_horizontal = None
        min_libre_vertical = None

        y_vals = sorted(list(set(round(bar["y"], 6) for bar in barras)))
        x_vals = sorted(list(set(round(bar["x"], 6) for bar in barras)))

        for y in y_vals:
            fila = [bar for bar in barras if round(bar["y"], 6) == y]
            fila = sorted(fila, key=lambda z: z["x"])
            for i in range(len(fila) - 1):
                libre = self._distancia_libre_entre_barras(fila[i], fila[i + 1])
                min_libre_horizontal = libre if min_libre_horizontal is None else min(min_libre_horizontal, libre)

        for x in x_vals:
            columna = [bar for bar in barras if round(bar["x"], 6) == x]
            columna = sorted(columna, key=lambda z: z["y"])
            for i in range(len(columna) - 1):
                libre = self._distancia_libre_entre_barras(columna[i], columna[i + 1])
                min_libre_vertical = libre if min_libre_vertical is None else min(min_libre_vertical, libre)

        if min_libre_horizontal is not None:
            ok = min_libre_horizontal >= min_sep
            lineas.append(f"- Separación libre longitudinal mínima = {min_libre_horizontal:.2f} mm {'✅' if ok else '❌'}")
            if not ok:
                errores.append("Separación libre longitudinal insuficiente.")

        if min_libre_vertical is not None:
            ok = min_libre_vertical >= min_sep
            lineas.append(f"- Separación libre transversal mínima = {min_libre_vertical:.2f} mm {'✅' if ok else '❌'}")
            if not ok:
                errores.append("Separación libre transversal insuficiente.")

        ok_s = s_estribo_adoptada_mm <= s_max
        lineas.append(f"- Espaciamiento vertical de estribos = {s_estribo_adoptada_mm:.2f} mm {'✅' if ok_s else '❌'}")
        if not ok_s:
            errores.append("Espaciamiento vertical de estribos excede el máximo.")

        ok_d = d_st >= min_db_tie
        lineas.append(f"- Diámetro de estribo = {d_st:.2f} mm {'✅' if ok_d else '❌'}")
        if not ok_d:
            errores.append("Diámetro de estribo menor al mínimo.")

        return {
            "cumple": len(errores) == 0,
            "errores": errores,
            "texto": "\n".join(lineas),
            "min_libre_horizontal_mm": min_libre_horizontal,
            "min_libre_vertical_mm": min_libre_vertical,
        }

    def _check_cuantia(self, b, h, As_total):
        norma = self._norma_actual()
        Ag = b * h
        rho = As_total / Ag
        As_min = norma["rho_min_col"] * Ag
        As_max = norma["rho_max_col"] * Ag

        errores = []
        lineas = []
        lineas.append("2. ARMADURA MÍNIMA Y MÁXIMA")
        lineas.append(f"- Ag = {Ag:.2f} mm²")
        lineas.append(f"- As = {As_total:.2f} mm²")
        lineas.append(f"- ρ = {rho:.5f}")
        lineas.append(f"- As mínimo = {As_min:.2f} mm²")
        lineas.append(f"- As máximo = {As_max:.2f} mm²")

        ok_min = As_total >= As_min
        ok_max = As_total <= As_max

        lineas.append(f"- Cumple mínimo {'✅' if ok_min else '❌'}")
        lineas.append(f"- Cumple máximo {'✅' if ok_max else '❌'}")

        if not ok_min:
            errores.append("Armadura longitudinal menor al mínimo.")
        if not ok_max:
            errores.append("Armadura longitudinal mayor al máximo.")

        return {
            "cumple": len(errores) == 0,
            "errores": errores,
            "texto": "\n".join(lineas),
            "Ag": Ag,
            "rho": rho,
            "As_min": As_min,
            "As_max": As_max,
        }

    def _obtener_factor_rigidez_efectiva(self):
        if not self.usar_rigidez_efectiva.isChecked():
            return None

        factor = float(self.factor_rigidez_efectiva.text())
        if factor <= 0:
            raise ValueError("El factor de rigidez efectiva debe ser mayor que cero.")
        return factor

    def _check_esbeltez(self, b, h, fc, lu_x, lu_y, k_x, k_y):
        Ec = self._Ec_nb_mpa(fc)
        factor_rigidez = self._obtener_factor_rigidez_efectiva()

        Ag = b * h
        Ix = b * (h ** 3) / 12.0
        Iy = h * (b ** 3) / 12.0
        rx = self._radio_giro(Ix, Ag)
        ry = self._radio_giro(Iy, Ag)

        klu_x = k_x * lu_x
        klu_y = k_y * lu_y

        Pc_x = (math.pi ** 2) * 0.25 * Ec * Ix / (klu_x ** 2) / 1000.0 if klu_x > 0 else 0.0
        Pc_y = (math.pi ** 2) * 0.25 * Ec * Iy / (klu_y ** 2) / 1000.0 if klu_y > 0 else 0.0

        slim_x = klu_x / rx if rx > 0 else 999.0
        slim_y = klu_y / ry if ry > 0 else 999.0

        lineas = []
        lineas.append("3. ESBELTEZ / ESTABILIDAD")
        lineas.append(f"- Ec ≈ {Ec:.2f} MPa")
        lineas.append(f"- Ix = {Ix:.2f} mm⁴")
        lineas.append(f"- Iy = {Iy:.2f} mm⁴")
        lineas.append(f"- rx = {rx:.2f} mm")
        lineas.append(f"- ry = {ry:.2f} mm")
        lineas.append(f"- k·lu X = {klu_x:.2f} mm")
        lineas.append(f"- k·lu Y = {klu_y:.2f} mm")
        lineas.append(f"- (k·lu/r)x = {slim_x:.2f}")
        lineas.append(f"- (k·lu/r)y = {slim_y:.2f}")
        lineas.append(f"- Pc_x ≈ {Pc_x:.2f} kN")
        lineas.append(f"- Pc_y ≈ {Pc_y:.2f} kN")

        Pc_eff_x = None
        Pc_eff_y = None
        if factor_rigidez is not None:
            Ec_eff = factor_rigidez * Ec
            Pc_eff_x = (math.pi ** 2) * 0.25 * Ec_eff * Ix / (klu_x ** 2) / 1000.0 if klu_x > 0 else 0.0
            Pc_eff_y = (math.pi ** 2) * 0.25 * Ec_eff * Iy / (klu_y ** 2) / 1000.0 if klu_y > 0 else 0.0
            lineas.append(f"- Factor de rigidez efectiva activo = {factor_rigidez:.3f}")
            lineas.append(f"- Pc_x con rigidez efectiva ≈ {Pc_eff_x:.2f} kN (referencia)")
            lineas.append(f"- Pc_y con rigidez efectiva ≈ {Pc_eff_y:.2f} kN (referencia)")
        else:
            lineas.append("- Factor de rigidez efectiva inactivo: se mantiene la verificación base.")

        return {
            "texto": "\n".join(lineas),
            "Ec": Ec,
            "Ix": Ix,
            "Iy": Iy,
            "rx": rx,
            "ry": ry,
            "klu_x": klu_x,
            "klu_y": klu_y,
            "Pc_x": Pc_x,
            "Pc_y": Pc_y,
            "Pc_eff_x": Pc_eff_x,
            "Pc_eff_y": Pc_eff_y,
            "slim_x": slim_x,
            "slim_y": slim_y,
        }

    def _alpha_biaxial_aprox(self, pu, phi_po):
        if phi_po <= 0:
            return 1.0
        relacion = pu / phi_po
        alpha = 1.0 + relacion
        return max(1.0, min(2.0, alpha))

    def _indice_biaxial_aprox(self, mux, muy, cap_mx, cap_my, pu, phi_po):
        if cap_mx is None or cap_my is None:
            return None, None
        if cap_mx <= 0 or cap_my <= 0:
            return None, None

        alpha = self._alpha_biaxial_aprox(pu, phi_po)
        indice = (abs(mux) / cap_mx) ** alpha + (abs(muy) / cap_my) ** alpha
        return indice, alpha

    def _check_solicitaciones_normales(self, pu, mux, muy, cap_mx, cap_my, phiPo, Pc_x, Pc_y):
        errores = []
        lineas = []
        lineas.append("4. SOLICITACIONES NORMALES")

        limite_x = 0.75 * Pc_x
        limite_y = 0.75 * Pc_y

        ok_ax_x = pu <= limite_x if limite_x > 0 else False
        ok_ax_y = pu <= limite_y if limite_y > 0 else False

        lineas.append(f"- Pu = {pu:.2f} kN")
        lineas.append(f"- 0.75 Pc_x = {limite_x:.2f} kN {'✅' if ok_ax_x else '❌'}")
        lineas.append(f"- 0.75 Pc_y = {limite_y:.2f} kN {'✅' if ok_ax_y else '❌'}")

        if not ok_ax_x:
            errores.append("Pu excede 0.75·Pc en eje X.")
        if not ok_ax_y:
            errores.append("Pu excede 0.75·Pc en eje Y.")

        ok_phiPn = pu <= phiPo if phiPo > 0 else False
        lineas.append(f"- φPn máximo = {phiPo:.2f} kN {'✅' if ok_phiPn else '❌'}")
        if not ok_phiPn:
            errores.append("Pu excede φPn máximo.")

        indice_biaxial, alpha_biaxial = self._indice_biaxial_aprox(
            mux=mux, muy=muy, cap_mx=cap_mx, cap_my=cap_my, pu=pu, phi_po=phiPo
        )

        if indice_biaxial is None:
            errores.append("No se pudo calcular índice biaxial.")
            lineas.append("- Índice biaxial = No disponible ❌")
        else:
            lineas.append(f"- φMnX para Pu = {cap_mx:.2f} kN·m")
            lineas.append(f"- φMnY para Pu = {cap_my:.2f} kN·m")
            lineas.append(
                f"- Índice biaxial ≈ {indice_biaxial:.4f} con α = {alpha_biaxial:.3f} "
                f"{'✅' if indice_biaxial <= 1.0 else '❌'}"
            )
            if indice_biaxial > 1.0:
                errores.append("No cumple interacción biaxial aproximada.")

        return {
            "cumple": len(errores) == 0,
            "errores": errores,
            "texto": "\n".join(lineas),
            "indice_biaxial": indice_biaxial,
            "alpha_biaxial": alpha_biaxial,
        }

    def _diagnostico_preliminar(self, pu, mux, muy, phiPo, cap_mx, cap_my, disp, cuantia, normales):
        norma = self._norma_actual()
        ratio_axial = pu / phiPo if phiPo and phiPo > 0 else None
        ratio_mx = abs(mux) / cap_mx if cap_mx and cap_mx > 0 else None
        ratio_my = abs(muy) / cap_my if cap_my and cap_my > 0 else None
        ratio_biaxial = normales.get("indice_biaxial")

        ratios_validos = [r for r in [ratio_axial, ratio_mx, ratio_my, ratio_biaxial] if r is not None]
        ratio_control = max(ratios_validos) if ratios_validos else None

        min_sep = norma["clear_spacing_min_mm"]
        sep_no_cumple = (
            (disp.get("min_libre_horizontal_mm") is not None and disp["min_libre_horizontal_mm"] < min_sep) or
            (disp.get("min_libre_vertical_mm") is not None and disp["min_libre_vertical_mm"] < min_sep)
        )
        cuantia_alta = cuantia["rho"] >= 0.85 * norma["rho_max_col"]

        if sep_no_cumple or cuantia_alta:
            categoria = "Posible sobrearmado"
            mensaje = "Posible sobrearmado: revisar cantidad, diámetro o distribución de barras."
        elif ratio_control is None:
            categoria = "Diagnóstico no disponible"
            mensaje = "Diagnóstico preliminar no disponible: revisar la capacidad calculada para la combinación evaluada."
        elif ratio_control > 1.00:
            categoria = "No cumple"
            mensaje = "No cumple: aumentar sección o acero."
        elif ratio_control >= 0.85:
            categoria = "Cumple ajustado"
            mensaje = "Cumple ajustado: verificar con CYPE antes de optimizar."
        elif ratio_control >= 0.55:
            categoria = "Cumple adecuadamente"
            mensaje = "Cumple adecuadamente: sección razonable."
        elif ratio_control < 0.50:
            categoria = "Posible sobredimensionamiento"
            mensaje = "Posible sobredimensionamiento: probar una sección menor en CYPE."
        else:
            categoria = "Cumple adecuadamente"
            mensaje = "Cumple adecuadamente: sección razonable."

        detalles = []
        if ratio_axial is not None:
            detalles.append(f"- Pu/φPn ≈ {ratio_axial:.3f}")
        if ratio_mx is not None:
            detalles.append(f"- Mux/φMnX ≈ {ratio_mx:.3f}")
        if ratio_my is not None:
            detalles.append(f"- Muy/φMnY ≈ {ratio_my:.3f}")
        if ratio_biaxial is not None:
            detalles.append(f"- Índice biaxial de control ≈ {ratio_biaxial:.3f}")
        if ratio_control is not None:
            detalles.append(f"- Relación demanda/capacidad de control ≈ {ratio_control:.3f}")
        if cuantia_alta:
            detalles.append(f"- Cuantía alta detectada: ρ = {cuantia['rho']:.5f}")
        if sep_no_cumple:
            detalles.append("- La separación libre entre barras no cumple el mínimo normativo.")

        return {
            "categoria": categoria,
            "mensaje": mensaje,
            "ratio_control": ratio_control,
            "ratio_axial": ratio_axial,
            "ratio_mx": ratio_mx,
            "ratio_my": ratio_my,
            "ratio_biaxial": ratio_biaxial,
            "texto": "\n".join(["=== DIAGNÓSTICO PRELIMINAR ===", mensaje, *detalles]),
        }

    def _ratio_control_config(self, pu, mux, muy, phiPo, cap_mx, cap_my, indice_biaxial):
        ratios = []
        if phiPo is not None and phiPo > 0:
            ratios.append(pu / phiPo)
        if cap_mx is not None and cap_mx > 0:
            ratios.append(abs(mux) / cap_mx)
        if cap_my is not None and cap_my > 0:
            ratios.append(abs(muy) / cap_my)
        if indice_biaxial is not None:
            ratios.append(indice_biaxial)
        return max(ratios) if ratios else None

    def _check_cortante(self, b, h, fc, Nu_kN, vx_kN, vy_kN, fy_t, ramas_x, ramas_y, db_t, rec_t):
        phi_v = 0.75
        d_long = self._diametro_a_mm(float(self.db_esquinas.currentText()))
        d_x = h - rec_t - db_t - d_long / 2.0
        d_y = b - rec_t - db_t - d_long / 2.0

        if d_x <= 0 or d_y <= 0:
            return {
                "cumple": False,
                "errores": ["Profundidad útil inválida para cortante."],
                "texto": "5. CORTANTE\n- Profundidad útil inválida ❌"
            }

        Av_x = ramas_x * self._bar_area_mm2(db_t)
        Av_y = ramas_y * self._bar_area_mm2(db_t)
        s_adopt = self._longitud_a_mm(float(self.sep_estribo_adoptada.text()))

        if s_adopt <= 0:
            return {
                "cumple": False,
                "errores": ["Separación adoptada inválida."],
                "texto": "5. CORTANTE\n- Separación adoptada inválida ❌"
            }

        Nu_N = Nu_kN * 1000.0
        Ag = b * h

        vc_x = (0.17 * math.sqrt(fc) + min(Nu_N / (6.0 * Ag), 0.3 * math.sqrt(fc))) * b * d_x / 1000.0
        vc_y = (0.17 * math.sqrt(fc) + min(Nu_N / (6.0 * Ag), 0.3 * math.sqrt(fc))) * h * d_y / 1000.0

        Vs_x = Av_x * fy_t * d_x / s_adopt / 1000.0
        Vs_y = Av_y * fy_t * d_y / s_adopt / 1000.0

        Vn_x = vc_x + Vs_x
        Vn_y = vc_y + Vs_y

        phiVn_x = phi_v * Vn_x
        phiVn_y = phi_v * Vn_y

        ok_x = vx_kN <= phiVn_x
        ok_y = vy_kN <= phiVn_y

        errores = []
        if not ok_x:
            errores.append("No cumple a cortante en X.")
        if not ok_y:
            errores.append("No cumple a cortante en Y.")

        lineas = []
        lineas.append("5. CORTANTE")
        lineas.append(f"- Vu_x = {vx_kN:.2f} kN ; φVn_x = {phiVn_x:.2f} kN {'✅' if ok_x else '❌'}")
        lineas.append(f"- Vu_y = {vy_kN:.2f} kN ; φVn_y = {phiVn_y:.2f} kN {'✅' if ok_y else '❌'}")
        lineas.append(f"- Vc_x = {vc_x:.2f} kN ; Vs_x = {Vs_x:.2f} kN")
        lineas.append(f"- Vc_y = {vc_y:.2f} kN ; Vs_y = {Vs_y:.2f} kN")
        lineas.append(f"- s adoptada = {s_adopt:.2f} mm")

        return {
            "cumple": len(errores) == 0,
            "errores": errores,
            "texto": "\n".join(lineas),
            "phiVn_x": phiVn_x,
            "phiVn_y": phiVn_y,
        }

    # ======================================================
    # AUTOMATICO
    # ======================================================
    def _evaluar_configuracion(self, b, h, fc, fy, d_st, pu, mux, muy, lu_x, lu_y, k_x, k_y,
                               n_cx, n_cy, d_esq_mm, d_x_mm, d_y_mm):
        try:
            barras = self._generar_barras_reales(
                b=b, h=h, d_st=d_st,
                n_cx=n_cx, n_cy=n_cy,
                d_esq=d_esq_mm, d_x=d_x_mm, d_y=d_y_mm
            )
        except Exception:
            return None

        As_total = sum(bar["area"] for bar in barras)
        cuantia = self._check_cuantia(b, h, As_total)
        disp = self._check_disposicion_armaduras(
            b, h, barras, d_st,
            self._longitud_a_mm(float(self.sep_estribo_adoptada.text()))
        )
        esb = self._check_esbeltez(b, h, fc, lu_x, lu_y, k_x, k_y)

        curva_x, _, _, _, _ = self._diagrama_interaccion_uniaxial(b, h, fc, fy, barras, eje="X")
        curva_y, _, _, _, _ = self._diagrama_interaccion_uniaxial(b, h, fc, fy, barras, eje="Y")

        cap_mx = self._capacidad_momento_para_pu(curva_x, pu)
        cap_my = self._capacidad_momento_para_pu(curva_y, pu)

        if cap_mx is None or cap_my is None:
            return {"cumple": False, "motivo": "La carga axial está fuera del rango útil de la curva."}

        Po = 0.85 * fc * (b * h - As_total) + fy * As_total
        phiPo = self._norma_actual()["phi_min"] * 0.80 * Po / 1000.0

        normales = self._check_solicitaciones_normales(
            pu=pu, mux=mux, muy=muy,
            cap_mx=cap_mx, cap_my=cap_my,
            phiPo=phiPo, Pc_x=esb["Pc_x"], Pc_y=esb["Pc_y"]
        )

        cumple = cuantia["cumple"] and disp["cumple"] and normales["cumple"]

        return {
            "cumple": cumple,
            "cuantia": cuantia,
            "disp": disp,
            "normales": normales,
            "As_total": As_total,
            "total_barras": self._contar_barras(barras),
            "barras": barras,
            "d_esq_mm": d_esq_mm,
            "d_x_mm": d_x_mm,
            "d_y_mm": d_y_mm,
            "cap_mx": cap_mx,
            "cap_my": cap_my,
        }

    def _diagnostico_diseno_automatico(self, b, h, fc, fy, d_st, pu, mux, muy, lu_x, lu_y, k_x, k_y):
        resumen = {
            "cuantia": 0,
            "disposicion": 0,
            "solicitaciones": 0,
            "curva": 0,
            "geometria": 0,
        }
        ejemplos = []
        lista_d = self._lista_barras_disponibles()

        for d_esq in lista_d:
            d_esq_mm = d_esq if self.unidad_diametro_barra == "mm" else d_esq * 10.0
            for d_x in lista_d:
                d_x_mm = d_x if self.unidad_diametro_barra == "mm" else d_x * 10.0
                for d_y in lista_d:
                    d_y_mm = d_y if self.unidad_diametro_barra == "mm" else d_y * 10.0
                    for n_cx in range(0, 9):
                        for n_cy in range(0, 9):
                            total = 4 + 2 * n_cx + 2 * n_cy
                            if total < self.nmin_total.value() or total > self.nmax_total.value():
                                continue

                            r = self._evaluar_configuracion(
                                b, h, fc, fy, d_st, pu, mux, muy, lu_x, lu_y, k_x, k_y,
                                n_cx=n_cx, n_cy=n_cy,
                                d_esq_mm=d_esq_mm, d_x_mm=d_x_mm, d_y_mm=d_y_mm
                            )

                            desc = (
                                f"{total} barras "
                                f"(Esq Ø{int(round(d_esq_mm))}, X Ø{int(round(d_x_mm))}, Y Ø{int(round(d_y_mm))}) "
                                f"(Cara X={n_cx}, Cara Y={n_cy})"
                            )

                            if r is None:
                                resumen["geometria"] += 1
                                if len(ejemplos) < 6:
                                    ejemplos.append(f"- {desc}: no cabe geométricamente en la sección.")
                                continue

                            if not r["cuantia"]["cumple"]:
                                resumen["cuantia"] += 1
                                if len(ejemplos) < 6:
                                    ejemplos.append(f"- {desc}: falla por cuantía mínima/máxima.")
                                continue

                            if not r["disp"]["cumple"]:
                                resumen["disposicion"] += 1
                                if len(ejemplos) < 6:
                                    ejemplos.append(f"- {desc}: falla por disposición / separación.")
                                continue

                            if not r["normales"]["cumple"]:
                                if r["normales"]["indice_biaxial"] is None:
                                    resumen["curva"] += 1
                                    if len(ejemplos) < 6:
                                        ejemplos.append(f"- {desc}: Pu fuera del rango útil o sin curva válida.")
                                else:
                                    resumen["solicitaciones"] += 1
                                    if len(ejemplos) < 6:
                                        ejemplos.append(
                                            f"- {desc}: falla por solicitaciones normales "
                                            f"(índice biaxial ≈ {r['normales']['indice_biaxial']:.3f})."
                                        )
                                continue

        texto = []
        texto.append("=== DIAGNÓSTICO DEL DISEÑO AUTOMÁTICO ===")
        texto.append("")
        texto.append(f"- Casos descartados por cuantía: {resumen['cuantia']}")
        texto.append(f"- Casos descartados por disposición: {resumen['disposicion']}")
        texto.append(f"- Casos descartados por solicitaciones normales: {resumen['solicitaciones']}")
        texto.append(f"- Casos descartados por curva / rango axial: {resumen['curva']}")
        texto.append(f"- Casos descartados por geometría: {resumen['geometria']}")
        texto.append("")
        texto.append("Ejemplos de intentos fallidos:")
        if ejemplos:
            texto.extend(ejemplos)
        else:
            texto.append("- No se generaron ejemplos.")

        return "\n".join(texto), resumen

    def _generar_sugerencias_diseno(self, b, h, fc, fy, d_st, pu, mux, muy, lu_x, lu_y, k_x, k_y):
        sugerencias = []
        lista_d = self._lista_barras_disponibles()

        for d_esq in sorted(lista_d):
            d_esq_mm = d_esq if self.unidad_diametro_barra == "mm" else d_esq * 10.0
            for d_x in sorted(lista_d):
                d_x_mm = d_x if self.unidad_diametro_barra == "mm" else d_x * 10.0
                for d_y in sorted(lista_d):
                    d_y_mm = d_y if self.unidad_diametro_barra == "mm" else d_y * 10.0
                    for n_cx in range(2, 9):
                        for n_cy in range(2, 9):
                            r = self._evaluar_configuracion(
                                b, h, fc, fy, d_st, pu, mux, muy, lu_x, lu_y, k_x, k_y,
                                n_cx=n_cx, n_cy=n_cy,
                                d_esq_mm=d_esq_mm, d_x_mm=d_x_mm, d_y_mm=d_y_mm
                            )
                            if r and r["cumple"]:
                                sugerencias.append(
                                    f"- Con la misma sección, prueba {r['total_barras']} barras "
                                    f"(Esq Ø{int(round(d_esq_mm))}, X Ø{int(round(d_x_mm))}, Y Ø{int(round(d_y_mm))})."
                                )
                                return sugerencias

        incrementos = [(50, 0), (0, 50), (50, 50), (100, 0), (0, 100)]
        for db, dh in incrementos:
            b2 = b + db
            h2 = h + dh
            for d_esq in sorted(lista_d):
                d_esq_mm = d_esq if self.unidad_diametro_barra == "mm" else d_esq * 10.0
                for d_x in sorted(lista_d):
                    d_x_mm = d_x if self.unidad_diametro_barra == "mm" else d_x * 10.0
                    for d_y in sorted(lista_d):
                        d_y_mm = d_y if self.unidad_diametro_barra == "mm" else d_y * 10.0
                        for n_cx in range(2, 7):
                            for n_cy in range(2, 7):
                                r = self._evaluar_configuracion(
                                    b2, h2, fc, fy, d_st, pu, mux, muy, lu_x, lu_y, k_x, k_y,
                                    n_cx=n_cx, n_cy=n_cy,
                                    d_esq_mm=d_esq_mm, d_x_mm=d_x_mm, d_y_mm=d_y_mm
                                )
                                if r and r["cumple"]:
                                    sugerencias.append(
                                        f"- Aumenta la sección a {b2:.0f}x{h2:.0f} mm y prueba {r['total_barras']} barras "
                                        f"(Esq Ø{int(round(d_esq_mm))}, X Ø{int(round(d_x_mm))}, Y Ø{int(round(d_y_mm))})."
                                    )
                                    return sugerencias

        Ec = self._Ec_nb_mpa(fc)
        Ix = b * (h ** 3) / 12.0
        Iy = h * (b ** 3) / 12.0
        Pc_x = (math.pi ** 2) * 0.25 * Ec * Ix / ((k_x * lu_x) ** 2) / 1000.0 if k_x * lu_x > 0 else 0
        Pc_y = (math.pi ** 2) * 0.25 * Ec * Iy / ((k_y * lu_y) ** 2) / 1000.0 if k_y * lu_y > 0 else 0

        if pu > 0.75 * Pc_x or pu > 0.75 * Pc_y:
            sugerencias.append("- El problema dominante parece ser de estabilidad: aumenta sección, reduce lu o reduce k.")
        else:
            sugerencias.append("- El problema dominante parece ser de resistencia de sección: aumenta acero longitudinal o sección.")

        if self._longitud_a_mm(float(self.sep_estribo_adoptada.text())) > self._norma_actual()["max_tie_spacing_rule_mm"]:
            sugerencias.append("- Reduce la separación de estribos; la separación actual excede el máximo recomendado.")

        sugerencias.append("- Revisa también la disposición de barras y los recubrimientos.")
        return sugerencias

    def _buscar_diseno_automatico(self, b, h, fc, fy, d_st, pu, mux, muy, lu_x, lu_y, k_x, k_y):
        nmin = self.nmin_total.value()
        nmax = self.nmax_total.value()

        if nmin > nmax:
            raise ValueError("El total mínimo de barras no puede ser mayor que el máximo.")

        soluciones = []
        lista_d = self._lista_barras_disponibles()

        for d_esq in lista_d:
            d_esq_mm = d_esq if self.unidad_diametro_barra == "mm" else d_esq * 10.0
            for d_x in lista_d:
                d_x_mm = d_x if self.unidad_diametro_barra == "mm" else d_x * 10.0
                for d_y in lista_d:
                    d_y_mm = d_y if self.unidad_diametro_barra == "mm" else d_y * 10.0
                    for n_cx in range(0, 9):
                        for n_cy in range(0, 9):
                            total = 4 + 2 * n_cx + 2 * n_cy
                            if total < nmin or total > nmax:
                                continue

                            r = self._evaluar_configuracion(
                                b, h, fc, fy, d_st, pu, mux, muy, lu_x, lu_y, k_x, k_y,
                                n_cx=n_cx, n_cy=n_cy,
                                d_esq_mm=d_esq_mm, d_x_mm=d_x_mm, d_y_mm=d_y_mm
                            )
                            if r and r["cumple"]:
                                po = 0.85 * fc * (b * h - r["As_total"]) + fy * r["As_total"]
                                phi_po = self._norma_actual()["phi_min"] * 0.80 * po / 1000.0
                                ratio_control = self._ratio_control_config(
                                    pu=pu, mux=mux, muy=muy,
                                    phiPo=phi_po,
                                    cap_mx=r["cap_mx"],
                                    cap_my=r["cap_my"],
                                    indice_biaxial=r["normales"]["indice_biaxial"]
                                )
                                soluciones.append({
                                    "d_esq_mm": d_esq_mm,
                                    "d_x_mm": d_x_mm,
                                    "d_y_mm": d_y_mm,
                                    "n_cx": n_cx,
                                    "n_cy": n_cy,
                                    "total": r["total_barras"],
                                    "As_total_mm2": r["As_total"],
                                    "barras": r["barras"],
                                    "rho": r["cuantia"]["rho"],
                                    "cap_mx": r["cap_mx"],
                                    "cap_my": r["cap_my"],
                                    "indice_biaxial": r["normales"]["indice_biaxial"],
                                    "ratio_control": ratio_control if ratio_control is not None else 999.0,
                                })

        if not soluciones:
            return None

        soluciones.sort(
            key=lambda s: (
                abs(s["ratio_control"] - 0.75),
                s["As_total_mm2"],
                abs(s["n_cx"] - s["n_cy"]),
                s["total"],
                s["d_esq_mm"] + s["d_x_mm"] + s["d_y_mm"]
            )
        )
        return soluciones[0]

    # ======================================================
    # ESTRIBOS
    # ======================================================
    def calcular_estribos(self):
        try:
            norma = self._norma_actual()

            b = self._longitud_a_mm(float(self.b.text()))
            h = self._longitud_a_mm(float(self.h.text()))
            fc = float(self.fc.text())

            vx = float(self.vx_col.text()) * self._factor_fuerza_a_kN()
            vy = float(self.vy_col.text()) * self._factor_fuerza_a_kN()

            fy_t = float(self.fy_estribo.text())
            ramas_x = self.num_ramas_x.value()
            ramas_y = self.num_ramas_y.value()
            db_t = self._diametro_a_mm(float(self.db_estribo_combo.currentText()))
            altura = self._longitud_a_mm(float(self.altura_estribada.text()))
            rec_t = self._recubrimiento_a_mm(float(self.recubrimiento_estribo.text()))
            s_adopt = self._longitud_a_mm(float(self.sep_estribo_adoptada.text()))

            if b <= 0 or h <= 0:
                raise ValueError("b y h deben ser mayores que cero.")
            if vx < 0 or vy < 0:
                raise ValueError("Vx y Vy no deben ser negativos.")
            if fy_t <= 0 or db_t <= 0 or altura <= 0 or s_adopt <= 0:
                raise ValueError("fy, diámetro, separación y altura deben ser mayores que cero.")

            cortante = self._check_cortante(
                b=b, h=h, fc=fc,
                Nu_kN=float(self.pu.text()) * self._factor_fuerza_a_kN(),
                vx_kN=vx, vy_kN=vy,
                fy_t=fy_t,
                ramas_x=ramas_x, ramas_y=ramas_y,
                db_t=db_t, rec_t=rec_t
            )

            n_estribos = math.ceil(altura / s_adopt) + 1

            texto = []
            texto.append("=== DISEÑO / CHEQUEO DE ESTRIBOS ===")
            texto.append(f"Norma: {norma['nombre']}")
            texto.append("")
            texto.append(cortante["texto"])
            texto.append("")
            texto.append(f"- Altura a estribar = {altura:.2f} mm")
            texto.append(f"- Cantidad aproximada de estribos = {n_estribos}")

            self.texto_estribos.setPlainText("\n".join(texto))
            self.tabs.setCurrentWidget(self.tab_estribos)

        except Exception as e:
            QMessageBox.warning(self, "Error en estribos", f"Revisa los datos.\n\n{e}")

    # ======================================================
    # CALCULO PRINCIPAL
    # ======================================================
    def calcular(self):
        try:
            self._limpiar_salidas_previas()

            norma = self._norma_actual()
            tipo = self.tipo_calculo.currentText()
            modo = self.modo_columna.currentText()

            b_in = float(self.b.text())
            h_in = float(self.h.text())
            fc = float(self.fc.text())
            fy = float(self.fy.text())
            dst_in = float(self.dst.text())

            pu_ing = float(self.pu.text())
            mux_ing = float(self.mux.text())
            muy_ing = float(self.muy.text())

            lu_x_in = float(self.lu_x.text())
            lu_y_in = float(self.lu_y.text())
            k_x = float(self.k_x.text())
            k_y = float(self.k_y.text())
            e_min_in = float(self.e_min.text())

            b = self._longitud_a_mm(b_in)
            h = self._longitud_a_mm(h_in)
            d_st = self._diametro_a_mm(dst_in)
            lu_x = self._longitud_a_mm(lu_x_in)
            lu_y = self._longitud_a_mm(lu_y_in)
            e_min = self._longitud_a_mm(e_min_in)

            pu = pu_ing * self._factor_fuerza_a_kN()
            mux = mux_ing * self._factor_momento_a_kNm()
            muy = muy_ing * self._factor_momento_a_kNm()

            if b <= 0 or h <= 0:
                raise ValueError("b y h deben ser mayores que cero.")
            if fc <= 0 or fy <= 0:
                raise ValueError("f'c y fy deben ser mayores que cero.")
            if d_st <= 0:
                raise ValueError("El diámetro de estribo debe ser mayor que cero.")
            if lu_x <= 0 or lu_y <= 0:
                raise ValueError("lu_x y lu_y deben ser mayores que cero.")
            if k_x <= 0 or k_y <= 0:
                raise ValueError("k_x y k_y deben ser mayores que cero.")

            solucion_diseno = None
            recomendaciones = []
            diagnostico_auto = ""

            es_modo_manual = modo == "Verificación con acero definido"

            if es_modo_manual:
                barras = self._generar_barras_desde_ui(b, h, d_st)
            else:
                solucion_diseno = self._buscar_diseno_automatico(
                    b=b, h=h, fc=fc, fy=fy, d_st=d_st,
                    pu=pu, mux=mux, muy=muy,
                    lu_x=lu_x, lu_y=lu_y, k_x=k_x, k_y=k_y
                )

                if solucion_diseno is None:
                    diagnostico_auto, _ = self._diagnostico_diseno_automatico(
                        b=b, h=h, fc=fc, fy=fy, d_st=d_st,
                        pu=pu, mux=mux, muy=muy,
                        lu_x=lu_x, lu_y=lu_y, k_x=k_x, k_y=k_y
                    )
                    recomendaciones = self._generar_sugerencias_diseno(
                        b=b, h=h, fc=fc, fy=fy, d_st=d_st,
                        pu=pu, mux=mux, muy=muy,
                        lu_x=lu_x, lu_y=lu_y, k_x=k_x, k_y=k_y
                    )

                    self.ultimo_diagnostico_auto = diagnostico_auto
                    self.ultimas_sugerencias_auto = recomendaciones

                    self.texto_comprobaciones.setPlainText(
                        diagnostico_auto + "\n\n=== RECOMENDACIONES ===\n" + "\n".join(recomendaciones)
                    )
                    self.resultados_texto.setPlainText(
                        "=== DISEÑO AUTOMÁTICO ===\n\n"
                        "No se encontró una solución automática con la configuración actual.\n\n"
                        + "\n".join(recomendaciones)
                    )

                    self._actualizar_resumen_armado(
                        extra="No se encontró diseño automático.\n" + "\n".join(recomendaciones)
                    )
                    self.tabs.setCurrentWidget(self.tab_comprobaciones)
                    self._datos_modificados = False
                    self.lbl_dirty.setText("")
                    return

                self._aplicar_solucion_diseno(solucion_diseno)
                barras = solucion_diseno["barras"]

            As_total = sum(bar["area"] for bar in barras)
            area_mostrada = self._area_a_unidad_mostrada(As_total)

            ex_mm = (mux * 1e6 / (pu * 1e3)) if abs(pu) > 1e-9 else 0.0
            ey_mm = (muy * 1e6 / (pu * 1e3)) if abs(pu) > 1e-9 else 0.0
            ex_usada = max(abs(ex_mm), e_min)
            ey_usada = max(abs(ey_mm), e_min)

            s_estribo_adoptada_mm = self._longitud_a_mm(float(self.sep_estribo_adoptada.text()))

            disp = self._check_disposicion_armaduras(b, h, barras, d_st, s_estribo_adoptada_mm)
            cuantia = self._check_cuantia(b, h, As_total)
            esb = self._check_esbeltez(b, h, fc, lu_x, lu_y, k_x, k_y)

            curva_x, punto_comp_x, punto_bal_x, punto_flex_x, _ = self._diagrama_interaccion_uniaxial(
                b, h, fc, fy, barras, eje="X"
            )
            curva_y, punto_comp_y, punto_bal_y, punto_flex_y, _ = self._diagrama_interaccion_uniaxial(
                b, h, fc, fy, barras, eje="Y"
            )

            cap_mx = self._capacidad_momento_para_pu(curva_x, pu)
            cap_my = self._capacidad_momento_para_pu(curva_y, pu)

            cap_mx_p0 = self._capacidad_momento_para_pu(curva_x, 0.0)
            cap_my_p0 = self._capacidad_momento_para_pu(curva_y, 0.0)

            Po = 0.85 * fc * (b * h - As_total) + fy * As_total
            phiPo = norma["phi_min"] * 0.80 * Po / 1000.0
            Po_nom_kN = Po / 1000.0

            if es_modo_manual:
                normales = {
                    "cumple": True,
                    "texto": (
                        "4. CAPACIDAD FRENTE A SOLICITACIONES NORMALES\n"
                        "- En modo manual no se verifica contra cargas actuantes.\n"
                        "- Se reporta la capacidad resistente de la sección para el armado ingresado."
                    ),
                    "indice_biaxial": None,
                    "alpha_biaxial": None,
                }
                cortante = {
                    "cumple": True,
                    "texto": (
                        "5. CORTANTE\n"
                        "- En modo manual no se verifica cortante porque no se ingresan solicitaciones."
                    ),
                    "phiVn_x": None,
                    "phiVn_y": None,
                }
            else:
                normales = self._check_solicitaciones_normales(
                    pu=pu, mux=mux, muy=muy,
                    cap_mx=cap_mx, cap_my=cap_my,
                    phiPo=phiPo, Pc_x=esb["Pc_x"], Pc_y=esb["Pc_y"]
                )

                cortante = self._check_cortante(
                    b=b, h=h, fc=fc,
                    Nu_kN=pu,
                    vx_kN=float(self.vx_col.text()) * self._factor_fuerza_a_kN(),
                    vy_kN=float(self.vy_col.text()) * self._factor_fuerza_a_kN(),
                    fy_t=float(self.fy_estribo.text()),
                    ramas_x=self.num_ramas_x.value(),
                    ramas_y=self.num_ramas_y.value(),
                    db_t=self._diametro_a_mm(float(self.db_estribo_combo.currentText())),
                    rec_t=self._recubrimiento_a_mm(float(self.recubrimiento_estribo.text()))
                )

            cumple_global = disp["cumple"] and cuantia["cumple"]
            if not es_modo_manual:
                cumple_global = cumple_global and normales["cumple"] and cortante["cumple"]

            diagnostico = self._diagnostico_preliminar(
                pu=pu, mux=mux, muy=muy,
                phiPo=phiPo, cap_mx=cap_mx, cap_my=cap_my,
                disp=disp, cuantia=cuantia, normales=normales
            )

            extra_armado = ""
            if solucion_diseno is not None:
                extra_armado = (
                    f"Diseño automático adoptado: {solucion_diseno['total']} barras "
                    f"(Esq Ø{int(round(solucion_diseno['d_esq_mm']))}, "
                    f"X Ø{int(round(solucion_diseno['d_x_mm']))}, "
                    f"Y Ø{int(round(solucion_diseno['d_y_mm']))})"
                )

            self._actualizar_resumen_armado(area_mostrada, cuantia["rho"], extra=extra_armado)

            texto_comp = []
            texto_comp.append("=== COMPROBACIONES TIPO CYPE / NB ===")
            texto_comp.append("")
            texto_comp.append(disp["texto"])
            texto_comp.append("")
            texto_comp.append(cuantia["texto"])
            texto_comp.append("")
            texto_comp.append(normales["texto"])
            texto_comp.append("")
            texto_comp.append(esb["texto"])
            texto_comp.append("")
            texto_comp.append(cortante["texto"])
            texto_comp.append("")
            texto_comp.append(diagnostico["texto"])
            self.texto_comprobaciones.setPlainText("\n".join(texto_comp))

            resumen_color = "🟢" if cumple_global else "🔴"
            resumen_estado = "CUMPLE" if cumple_global else "NO CUMPLE"
            if es_modo_manual:
                resumen_color = "🟢" if cumple_global else "🟡"
                resumen_estado = "CAPACIDAD REPORTADA" if cumple_global else "REVISAR DETALLADO"

            texto = []
            texto.append("=== RESUMEN INGENIERIL DE COLUMNA ===")
            texto.append("")
            texto.append(f"{resumen_color} VEREDICTO FINAL: {resumen_estado}")
            texto.append("")
            texto.append("1. DATOS GENERALES")
            texto.append(f"- Norma: {norma['nombre']}")
            texto.append(f"- Tipo de cálculo: {tipo}")
            texto.append(f"- Modo: {modo}")
            texto.append("")
            texto.append("2. CONVERSIONES DE CARGA")
            if es_modo_manual:
                texto.append(f"- Pu de referencia ingresado = {pu_ing:.4f} {self.unidad_fuerza}")
                texto.append(f"- Pu de referencia convertido = {pu:.4f} kN")
                texto.append("- Los momentos mostrados se calculan para este valor de Pu.")
            else:
                texto.append(f"- Pu ingresado = {pu_ing:.4f} {self.unidad_fuerza}")
                texto.append(f"- Pu convertido = {pu:.4f} kN")
                texto.append(f"- Mux ingresado = {mux_ing:.4f} {self.unidad_momento}")
                texto.append(f"- Mux convertido = {mux:.4f} kN·m")
                texto.append(f"- Muy ingresado = {muy_ing:.4f} {self.unidad_momento}")
                texto.append(f"- Muy convertido = {muy:.4f} kN·m")
            texto.append("")
            texto.append("3. GEOMETRÍA Y MATERIALES")
            texto.append(f"- b = {b:.2f} mm")
            texto.append(f"- h = {h:.2f} mm")
            texto.append(f"- f'c = {fc:.2f} MPa")
            texto.append(f"- fy = {fy:.2f} MPa")
            texto.append(f"- Diámetro de estribo = {d_st:.2f} mm")
            texto.append("")
            texto.append("4. ARMADO REAL")
            texto.append(f"- Esquinas: 4 Ø{self.db_esquinas.currentText()}")
            texto.append(f"- Cara X: {self.n_cara_x.value()} por cara Ø{self.db_cara_x.currentText()}")
            texto.append(f"- Cara Y: {self.n_cara_y.value()} por cara Ø{self.db_cara_y.currentText()}")
            texto.append(f"- Total de barras: {self._total_barras_actual()}")
            texto.append(f"- As total = {area_mostrada:.2f} {self.unidad_area_acero}")
            texto.append(f"- Cuantía ρ = {cuantia['rho']:.5f}")
            texto.append("")
            texto.append("5. CAPACIDAD DEL ARMADO INGRESADO")
            texto.append(f"- Pn nominal máximo ≈ {Po_nom_kN:.2f} kN")
            texto.append(f"- φPn máximo ≈ {phiPo:.2f} kN")
            texto.append(f"- φMnX con P≈0 = {cap_mx_p0:.2f} kN·m" if cap_mx_p0 is not None else "- φMnX con P≈0 no disponible")
            texto.append(f"- φMnY con P≈0 = {cap_my_p0:.2f} kN·m" if cap_my_p0 is not None else "- φMnY con P≈0 no disponible")
            if es_modo_manual:
                texto.append(f"- φMnX para Pu de referencia = {cap_mx:.2f} kN·m" if cap_mx is not None else "- φMnX para Pu de referencia no disponible")
                texto.append(f"- φMnY para Pu de referencia = {cap_my:.2f} kN·m" if cap_my is not None else "- φMnY para Pu de referencia no disponible")
                texto.append("- Usa el diagrama de interacción para leer otras combinaciones P-Mx-My resistentes.")
            else:
                texto.append(f"- φMnX para Pu = {cap_mx:.2f} kN·m" if cap_mx is not None else "- φMnX para Pu no disponible")
                texto.append(f"- φMnY para Pu = {cap_my:.2f} kN·m" if cap_my is not None else "- φMnY para Pu no disponible")
                texto.append(f"- Índice biaxial ≈ {normales['indice_biaxial']:.4f}" if normales["indice_biaxial"] is not None else "- Índice biaxial no disponible")
            texto.append("")
            texto.append("6. EXCENTRICIDAD")
            if es_modo_manual:
                texto.append("- No aplica en este modo porque no se evalúan cargas actuantes.")
            else:
                texto.append(f"- ex geométrica = {ex_mm:.2f} mm")
                texto.append(f"- ey geométrica = {ey_mm:.2f} mm")
                texto.append(f"- e mínima adoptada = {e_min:.2f} mm")
                texto.append(f"- ex usada = {ex_usada:.2f} mm")
                texto.append(f"- ey usada = {ey_usada:.2f} mm")
            texto.append("")
            texto.append("7. ESBELTEZ")
            texto.append(f"- k·lu X = {esb['klu_x']:.2f} mm")
            texto.append(f"- k·lu Y = {esb['klu_y']:.2f} mm")
            texto.append(f"- (k·lu/r)x = {esb['slim_x']:.2f}")
            texto.append(f"- (k·lu/r)y = {esb['slim_y']:.2f}")
            texto.append(f"- Pc_x = {esb['Pc_x']:.2f} kN")
            texto.append(f"- Pc_y = {esb['Pc_y']:.2f} kN")
            texto.append("")
            texto.append("8. ESTADO")
            texto.append(f"- Disposición relativa de armaduras: {'✅' if disp['cumple'] else '❌'}")
            texto.append(f"- Armadura mínima y máxima: {'✅' if cuantia['cumple'] else '❌'}")
            if es_modo_manual:
                texto.append("- Solicitaciones normales: capacidad reportada, sin chequeo contra cargas.")
                texto.append("- Cortante: no evaluado en este modo.")
                texto.append(f"- Estado del detallado básico: {'✅' if cumple_global else '⚠️'}")
            else:
                texto.append(f"- Solicitaciones normales: {'✅' if normales['cumple'] else '❌'}")
                texto.append(f"- Cortante: {'✅' if cortante['cumple'] else '❌'}")
                texto.append(f"- Veredicto final: {'✅' if cumple_global else '❌'}")
            texto.append("")
            texto.append("9. DIAGNÓSTICO PRELIMINAR")
            texto.append(f"- Categoría: {diagnostico['categoria']}")
            texto.append(f"- Mensaje: {diagnostico['mensaje']}")
            texto.append(
                f"- Relación demanda/capacidad de control ≈ {diagnostico['ratio_control']:.3f}"
                if diagnostico["ratio_control"] is not None
                else "- Relación demanda/capacidad de control no disponible"
            )

            self.resultados_texto.setPlainText("\n".join(texto))

            texto_est = []
            texto_est.append("=== RESUMEN DE ESTRIBOS ===")
            texto_est.append("")
            texto_est.append(cortante["texto"])
            self.texto_estribos.setPlainText("\n".join(texto_est))

            self.ultimo_grafico = {
                "curva_x": curva_x,
                "curva_y": curva_y,
                "pu": pu,
                "mux": abs(mux),
                "muy": abs(muy),
                "punto_comp_x": punto_comp_x,
                "punto_bal_x": punto_bal_x,
                "punto_flex_x": punto_flex_x,
                "punto_comp_y": punto_comp_y,
                "punto_bal_y": punto_bal_y,
                "punto_flex_y": punto_flex_y,
                "cap_mx": cap_mx,
                "cap_my": cap_my,
                "cumple": cumple_global,
            }
            self._redibujar_ultimo_grafico()

            self.ultimo_resultado = {
                "tipo_calculo": tipo,
                "modo_columna": modo,
                "norma": norma["nombre"],
                "cumple": cumple_global,
                "diagnostico_preliminar": diagnostico["categoria"],
                "resumen_texto": "\n".join(texto),
                "comprobaciones_texto": "\n".join(texto_comp),
            }

            self._datos_modificados = False
            self.lbl_dirty.setText("")

        except Exception as e:
            QMessageBox.warning(self, "Error de datos", f"Revisa los valores ingresados.\n\n{e}")

    # ======================================================
    # GRAFICOS
    # ======================================================
    def _redibujar_ultimo_grafico(self):
        if not self.ultimo_grafico:
            return

        vista = self.combo_vista_diagrama.currentText()
        data = self.ultimo_grafico

        if vista == "2D - Eje X":
            self._graficar_2d_eje(
                curva=data["curva_x"],
                pu=data["pu"],
                mu=data["mux"],
                cap_mu=data["cap_mx"],
                nombre_eje="X",
                punto_comp=data["punto_comp_x"],
                punto_bal=data["punto_bal_x"],
                punto_flex=data["punto_flex_x"],
                cumple=(data["cap_mx"] is not None and data["mux"] <= data["cap_mx"])
            )
        elif vista == "2D - Eje Y":
            self._graficar_2d_eje(
                curva=data["curva_y"],
                pu=data["pu"],
                mu=data["muy"],
                cap_mu=data["cap_my"],
                nombre_eje="Y",
                punto_comp=data["punto_comp_y"],
                punto_bal=data["punto_bal_y"],
                punto_flex=data["punto_flex_y"],
                cumple=(data["cap_my"] is not None and data["muy"] <= data["cap_my"])
            )
        elif vista == "2D - Comparación tipo Excel":
            self._graficar_diagrama_excel(
                data["curva_x"], data["curva_y"],
                data["pu"], data["mux"], data["muy"],
                data["cap_mx"], data["cap_my"], data["cumple"]
            )
        else:
            self._graficar_superficie_3d(
                data["curva_x"], data["curva_y"],
                data["pu"], data["mux"], data["muy"], data["cumple"]
            )

    def _graficar_2d_eje(self, curva, pu, mu, cap_mu, nombre_eje, punto_comp, punto_bal, punto_flex, cumple):
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        if curva:
            m = np.array([p[0] for p in curva], dtype=float)
            p = np.array([p[1] for p in curva], dtype=float)

            color_punto = "green" if cumple else "red"

            ax.plot(m, p, linewidth=2.8, label=f"Curva P-M{nombre_eje}")
            ax.fill_between(m, p, alpha=0.16)
            ax.scatter([mu], [pu], s=90, color=color_punto, label="Punto actuante", zorder=6)

            if punto_comp is not None:
                ax.scatter([punto_comp[0]], [punto_comp[1]], s=55, label="Compresión pura", zorder=6)
            if punto_bal is not None:
                ax.scatter([punto_bal[0]], [punto_bal[1]], s=55, label="Punto balanceado", zorder=6)
            if punto_flex is not None:
                ax.scatter([punto_flex[0]], [punto_flex[1]], s=55, label="Flexión dominante", zorder=6)

            xmax = max(np.max(m), mu) * 1.15 if max(np.max(m), mu) > 0 else 1
            ymax = max(np.max(p), pu) * 1.15 if max(np.max(p), pu) > 0 else 1

            ax.set_xlim(0, xmax)
            ax.set_ylim(0, ymax)
            ax.set_xlabel(f"Momento M{nombre_eje} ({self.unidad_momento})")
            ax.set_ylabel(f"Carga axial ({self.unidad_fuerza})")
            ax.set_title(f"Diagrama clásico P-M{nombre_eje}")
            ax.grid(True)
            ax.legend(loc="upper right")
        else:
            ax.text(0.5, 0.5, "No hay datos para graficar.", ha="center", va="center")
            ax.set_axis_off()

        self.canvas.draw()

    def _graficar_diagrama_excel(self, curva_x, curva_y, pu, mux, muy, cap_mx, cap_my, cumple_global):
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        if curva_x and curva_y:
            mx = np.array([p[0] for p in curva_x], dtype=float)
            px = np.array([p[1] for p in curva_x], dtype=float)

            my = np.array([p[0] for p in curva_y], dtype=float)
            py = np.array([p[1] for p in curva_y], dtype=float)

            ax.plot(-mx, px, linewidth=2.5, label="MOMENTO EN X")
            ax.fill_between(-mx, px, alpha=0.12)
            ax.plot(my, py, linewidth=2.5, label="MOMENTO EN Y")
            ax.fill_between(my, py, alpha=0.12)
            ax.hlines(pu, xmin=-max(mx) * 1.05, xmax=max(my) * 1.05, linewidth=2.0, label="CARGA ÚLTIMA")

            color_x = "green" if (cap_mx is not None and mux <= cap_mx) else "red"
            color_y = "green" if (cap_my is not None and muy <= cap_my) else "red"

            ax.scatter([-mux], [pu], s=80, color=color_x, label="Carga externa X", zorder=6)
            ax.scatter([muy], [pu], s=80, color=color_y, marker="x", label="Carga externa Y", zorder=6)

            xmax = max(np.max(mx), np.max(my), mux, muy) * 1.18
            ymax = max(np.max(px), np.max(py), pu) * 1.15

            ax.set_xlim(-xmax, xmax)
            ax.set_ylim(min(-0.08 * ymax, -50), ymax)
            ax.set_title("Diagrama de interacción biaxial tipo Excel")
            ax.set_xlabel(f"Momento ({self.unidad_momento})   ← X | Y →")
            ax.set_ylabel(f"Carga axial ({self.unidad_fuerza})")
            ax.grid(True)
            ax.legend(loc="upper right")
        else:
            ax.text(0.5, 0.5, "No hay datos suficientes para graficar.", ha="center", va="center")
            ax.set_axis_off()

        self.canvas.draw()

    def _graficar_superficie_3d(self, curva_x, curva_y, pu, mux, muy, cumple):
        self.figure.clear()
        ax = self.figure.add_subplot(111, projection="3d")

        superficie = self._superficie_interaccion_3d(curva_x, curva_y)

        if superficie is not None:
            X, Y, Z = superficie
            ax.plot_surface(X, Y, Z, alpha=0.35, linewidth=0, antialiased=True)

            color_punto = "green" if cumple else "red"
            ax.scatter([mux], [muy], [pu], color=color_punto, s=90, label="Punto actuante")

            ax.set_xlabel(f"Mx ({self.unidad_momento})")
            ax.set_ylabel(f"My ({self.unidad_momento})")
            ax.set_zlabel(f"P ({self.unidad_fuerza})")
            ax.set_title("Superficie de interacción 3D")
            ax.legend()
        else:
            ax.text2D(0.3, 0.5, "No se pudo generar superficie", transform=ax.transAxes)

        self.canvas.draw()

    # ======================================================
    # LIMPIAR / GUARDAR
    # ======================================================
    def limpiar(self):
        self.ultimo_resultado = {}
        self.ultimo_grafico = {}

        self.tipo_calculo.setCurrentText("Compresión compuesta")
        self.modo_columna.setCurrentText("Verificación con acero definido")
        self.combo_norma.setCurrentIndex(0)

        self.b.setText(self._valor_tentativo_longitud(300))
        self.h.setText(self._valor_tentativo_longitud(400))
        self.fc.setText("28")
        self.fy.setText("420")
        self.dst.setText(self._valor_tentativo_diametro(8))

        self.n_cara_x.setValue(2)
        self.n_cara_y.setValue(2)

        self.db_esquinas.setCurrentText(self._valor_tentativo_diametro(12))
        self.db_cara_x.setCurrentText(self._valor_tentativo_diametro(12))
        self.db_cara_y.setCurrentText(self._valor_tentativo_diametro(12))

        self.c_x.setText(self._valor_tentativo_recubrimiento(30))
        self.c_y.setText(self._valor_tentativo_recubrimiento(30))

        self.combo_barras_diseno.setCurrentIndex(0)
        self.nmin_total.setValue(8)
        self.nmax_total.setValue(16)

        self.pu.setText("147")
        self.mux.setText("3.48")
        self.muy.setText("0.26")

        self.lu_x.setText(self._valor_tentativo_longitud(3000))
        self.lu_y.setText(self._valor_tentativo_longitud(3000))
        self.k_x.setText("1.00")
        self.k_y.setText("1.00")
        self.e_min.setText(self._valor_tentativo_longitud(20))
        self.usar_rigidez_efectiva.setChecked(False)
        self.factor_rigidez_efectiva.setText("0.15")

        self.psiA_col.setText("8000000")
        self.psiA_vig.setText("6000000")
        self.psiB_col.setText("8000000")
        self.psiB_vig.setText("6000000")
        self.lbl_psi_resultado.setText("ψA = -, ψB = -, k estimado = -")

        self.vx_col.setText("0.04")
        self.vy_col.setText("0.84")
        self.fy_estribo.setText("420")
        self.num_ramas_x.setValue(2)
        self.num_ramas_y.setValue(2)
        self.db_estribo_combo.setCurrentText(self._valor_tentativo_diametro(8))
        self.sep_estribo_adoptada.setText(self._valor_tentativo_longitud(140))
        self.altura_estribada.setText(self._valor_tentativo_longitud(3000))
        self.recubrimiento_estribo.setText(self._valor_tentativo_recubrimiento(30))

        self.texto_estribos.clear()
        self.resultados_texto.clear()
        self.texto_comprobaciones.clear()
        self.lbl_armado_auto.setText("Armado adoptado: pendiente de calcular")

        self.figure.clear()
        self.canvas.draw()

        self.figure_sec.clear()
        self.canvas_sec.draw()

        self._actualizar_texto_unidades()
        self._actualizar_visibilidad_momentos()
        self._actualizar_modo_columna()
        self._actualizar_croquis()

        self._datos_modificados = False
        self.lbl_dirty.setText("")

    def guardar(self):
        if not self.ultimo_resultado:
            QMessageBox.information(self, "Aviso", "Primero debes calcular.")
            return

        guardar_resultado("columnas", self.ultimo_resultado)
        QMessageBox.information(self, "Guardado", "Resultados de columnas guardados correctamente.")
