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
    QSpinBox,
    QScrollArea,
    QSizePolicy,
    QFrame,
)

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from data.storage import guardar_resultado, obtener_configuracion
from domain.unidades import (
    area_a_unidad_mostrada,
    carga_distribuida_a_kN_m,
    diametro_a_mm,
    fuerza_a_kN,
    longitud_a_mm,
    mm_a_diametro_usuario,
    mm_a_longitud_usuario,
    momento_a_kNm,
    recubrimiento_a_mm,
)
from domain.vigas_core import DatosViga, bar_area_mm2, calcular_viga, es_modo_manual
from reports.vigas_report import (
    generar_texto_armado,
    generar_texto_comprobaciones,
    generar_texto_resultados,
)


class VigasView(QWidget):
    def __init__(self):
        super().__init__()

        self.ultimo_resultado = {}
        self.ultimo_grafico = {}
        self._datos_modificados = False

        self.config = obtener_configuracion()
        self.unidad_fuerza = self.config.get("unidad_fuerza", "kN")
        self.unidad_momento = self.config.get("unidad_momento", "kN·m")
        self.unidad_longitud = self.config.get("unidad_longitud", "mm")
        self.unidad_recubrimiento = self.config.get("unidad_recubrimiento", "mm")
        self.unidad_diametro_barra = self.config.get("unidad_diametro_barra", "mm")
        self.unidad_area_acero = self.config.get("unidad_area_acero", "mm²")

        self.normas = {
            "ACI 318-19": {"phi_flex": 0.90, "phi_shear": 0.75, "phi_torsion": 0.75, "nombre": "ACI 318-19"},
            "ACI 318-25": {"phi_flex": 0.90, "phi_shear": 0.75, "phi_torsion": 0.75, "nombre": "ACI 318-25"},
            "NB 1225001": {"phi_flex": 0.90, "phi_shear": 0.75, "phi_torsion": 0.75, "nombre": "NB 1225001"},
        }

        layout_principal = QVBoxLayout(self)

        titulo = QLabel("MODULO VIGAS - ESTIMACION Y VERIFICACION PRELIMINAR")
        titulo.setStyleSheet("font-size: 16px; font-weight: bold; padding: 4px;")
        layout_principal.addWidget(titulo)

        self.tabs = QTabWidget()
        layout_principal.addWidget(self.tabs)

        self.tab_datos = QWidget()
        self.tab_comprobaciones = QWidget()
        self.tab_resultados = QWidget()
        self.tab_graficos = QWidget()

        self.tabs.addTab(self.tab_datos, "Datos")
        self.tabs.addTab(self.tab_comprobaciones, "Comprobaciones")
        self.tabs.addTab(self.tab_resultados, "Resultados")
        self.tabs.addTab(self.tab_graficos, "Graficos")

        self._crear_tab_datos()
        self._crear_tab_comprobaciones()
        self._crear_tab_resultados()
        self._crear_tab_graficos()

        self._actualizar_texto_unidades()
        self._actualizar_modo()
        self._conectar_actualizacion_croquis()
        self._conectar_entradas_recalculo()
        self._actualizar_graficos_geometria()

    # ======================================================
    # GENERALES
    # ======================================================
    def _norma_actual(self):
        return self.normas[self.combo_norma.currentText()]

    def _longitud_a_mm(self, valor):
        return longitud_a_mm(valor, self.unidad_longitud)

    def _mm_a_longitud_usuario(self, valor_mm):
        return mm_a_longitud_usuario(valor_mm, self.unidad_longitud)

    def _recubrimiento_a_mm(self, valor):
        return recubrimiento_a_mm(valor, self.unidad_recubrimiento)

    def _diametro_a_mm(self, valor):
        return diametro_a_mm(valor, self.unidad_diametro_barra)

    def _mm_a_diametro_usuario(self, valor_mm):
        return mm_a_diametro_usuario(valor_mm, self.unidad_diametro_barra)

    def _area_a_unidad_mostrada(self, area_mm2):
        return area_a_unidad_mostrada(area_mm2, self.unidad_area_acero)

    def _valor_tentativo_longitud(self, valor_mm):
        return str(self._mm_a_longitud_usuario(valor_mm))

    def _valor_tentativo_recubrimiento(self, valor_mm):
        if self.unidad_recubrimiento == "cm":
            return str(valor_mm / 10.0)
        return str(valor_mm)

    def _valor_tentativo_diametro(self, valor_mm):
        return str(self._mm_a_diametro_usuario(valor_mm))

    def _barras_combo_textos(self):
        if self.unidad_diametro_barra == "mm":
            return ["8", "10", "12", "14", "16", "18", "20", "22", "25", "28", "32"]
        return ["0.8", "1.0", "1.2", "1.4", "1.6", "1.8", "2.0", "2.2", "2.5", "2.8", "3.2"]

    def _diametros_disponibles_mm(self):
        return [self._diametro_a_mm(float(texto)) for texto in self._barras_combo_textos()]

    def _tipo_modo_manual(self):
        return es_modo_manual(self.modo_viga.currentText())

    # ======================================================
    # INTERFAZ
    # ======================================================
    def _crear_tab_datos(self):
        layout_externo = QVBoxLayout(self.tab_datos)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        layout_externo.addWidget(scroll)

        contenido = QWidget()
        scroll.setWidget(contenido)
        layout = QVBoxLayout(contenido)

        grupo_tipo = QGroupBox("1. Modo de trabajo")
        layout_tipo = QGridLayout()

        self.modo_viga = QComboBox()
        self.modo_viga.addItems([
            "Diseñar / estimar acero con cargas",
            "Verificar capacidad con acero ingresado",
        ])
        self.modo_viga.currentIndexChanged.connect(self._actualizar_modo)

        self.combo_norma = QComboBox()
        self.combo_norma.addItems(list(self.normas.keys()))
        self.combo_norma.currentIndexChanged.connect(self._actualizar_texto_unidades)

        self.tipo_apoyo = QComboBox()
        self.tipo_apoyo.addItems([
            "Simplemente apoyada",
            "Un extremo continuo",
            "Ambos extremos continuos",
            "Voladizo",
        ])
        self.tipo_apoyo.currentIndexChanged.connect(self._actualizar_graficos_geometria)

        layout_tipo.addWidget(QLabel("Modo"), 0, 0)
        layout_tipo.addWidget(self.modo_viga, 0, 1)
        layout_tipo.addWidget(QLabel("Norma"), 1, 0)
        layout_tipo.addWidget(self.combo_norma, 1, 1)
        layout_tipo.addWidget(QLabel("Tipo de apoyo"), 2, 0)
        layout_tipo.addWidget(self.tipo_apoyo, 2, 1)
        grupo_tipo.setLayout(layout_tipo)
        layout.addWidget(grupo_tipo)

        grupo_unidades = QGroupBox("2. Sistema de unidades activo")
        layout_unidades = QVBoxLayout()
        self.lbl_unidades = QLabel()
        self.lbl_unidades.setWordWrap(True)
        layout_unidades.addWidget(self.lbl_unidades)
        grupo_unidades.setLayout(layout_unidades)
        layout.addWidget(grupo_unidades)

        grupo_geom = QGroupBox("3. Geometria y materiales")
        layout_geom = QGridLayout()
        self.luz = QLineEdit(self._valor_tentativo_longitud(6000))
        self.bw = QLineEdit(self._valor_tentativo_longitud(250))
        self.h = QLineEdit(self._valor_tentativo_longitud(500))
        self.rec = QLineEdit(self._valor_tentativo_recubrimiento(30))
        self.db_estribo = QComboBox()
        self.db_estribo.addItems(self._barras_combo_textos())
        self.db_estribo.setCurrentText(self._valor_tentativo_diametro(8))
        self.dag = QLineEdit(self._valor_tentativo_longitud(19))
        self.fc = QLineEdit("28")
        self.fy = QLineEdit("420")
        self.fyt = QLineEdit("420")

        layout_geom.addWidget(QLabel(f"Luz L ({self.unidad_longitud})"), 0, 0)
        layout_geom.addWidget(self.luz, 0, 1)
        layout_geom.addWidget(QLabel(f"bw ({self.unidad_longitud})"), 1, 0)
        layout_geom.addWidget(self.bw, 1, 1)
        layout_geom.addWidget(QLabel(f"h ({self.unidad_longitud})"), 2, 0)
        layout_geom.addWidget(self.h, 2, 1)
        layout_geom.addWidget(QLabel(f"Recubrimiento ({self.unidad_recubrimiento})"), 3, 0)
        layout_geom.addWidget(self.rec, 3, 1)
        layout_geom.addWidget(QLabel(f"Diametro de estribo ({self.unidad_diametro_barra})"), 4, 0)
        layout_geom.addWidget(self.db_estribo, 4, 1)
        layout_geom.addWidget(QLabel(f"Tamaño maximo nominal del agregado dag ({self.unidad_longitud})"), 5, 0)
        layout_geom.addWidget(self.dag, 5, 1)
        layout_geom.addWidget(QLabel("f'c (MPa)"), 6, 0)
        layout_geom.addWidget(self.fc, 6, 1)
        layout_geom.addWidget(QLabel("fy (MPa)"), 7, 0)
        layout_geom.addWidget(self.fy, 7, 1)
        layout_geom.addWidget(QLabel("fyt (MPa)"), 8, 0)
        layout_geom.addWidget(self.fyt, 8, 1)
        grupo_geom.setLayout(layout_geom)
        layout.addWidget(grupo_geom)

        grupo_cargas = QGroupBox("4. Cargas y esfuerzos")
        layout_cargas = QGridLayout()
        self.wu = QLineEdit("22")
        self.puntual = QLineEdit("0")
        self.x_p = QLineEdit(self._valor_tentativo_longitud(3000))
        self.mu_pos = QLineEdit("120")
        self.mu_neg_i = QLineEdit("80")
        self.mu_neg_d = QLineEdit("80")
        self.vu_i = QLineEdit("95")
        self.vu_d = QLineEdit("95")
        self.tu = QLineEdit("0")
        self.pu = QLineEdit("0")

        layout_cargas.addWidget(QLabel(f"wu ({self.unidad_fuerza}/{self.unidad_longitud})"), 0, 0)
        layout_cargas.addWidget(self.wu, 0, 1)
        layout_cargas.addWidget(QLabel(f"Carga puntual P ({self.unidad_fuerza})"), 1, 0)
        layout_cargas.addWidget(self.puntual, 1, 1)
        layout_cargas.addWidget(QLabel(f"Posicion x de P ({self.unidad_longitud})"), 2, 0)
        layout_cargas.addWidget(self.x_p, 2, 1)
        layout_cargas.addWidget(QLabel(f"Mu positivo en vano ({self.unidad_momento})"), 3, 0)
        layout_cargas.addWidget(self.mu_pos, 3, 1)
        layout_cargas.addWidget(QLabel(f"Mu negativo izquierdo ({self.unidad_momento})"), 4, 0)
        layout_cargas.addWidget(self.mu_neg_i, 4, 1)
        layout_cargas.addWidget(QLabel(f"Mu negativo derecho ({self.unidad_momento})"), 5, 0)
        layout_cargas.addWidget(self.mu_neg_d, 5, 1)
        layout_cargas.addWidget(QLabel(f"Vu izquierdo ({self.unidad_fuerza})"), 6, 0)
        layout_cargas.addWidget(self.vu_i, 6, 1)
        layout_cargas.addWidget(QLabel(f"Vu derecho ({self.unidad_fuerza})"), 7, 0)
        layout_cargas.addWidget(self.vu_d, 7, 1)
        layout_cargas.addWidget(QLabel(f"Tu ({self.unidad_momento})"), 8, 0)
        layout_cargas.addWidget(self.tu, 8, 1)
        layout_cargas.addWidget(QLabel(f"Pu axial real ({self.unidad_fuerza})"), 9, 0)
        layout_cargas.addWidget(self.pu, 9, 1)
        grupo_cargas.setLayout(layout_cargas)
        layout.addWidget(grupo_cargas)

        fila_armado = QHBoxLayout()

        grupo_armado = QGroupBox("5. Armado longitudinal y estribos")
        layout_armado = QGridLayout()
        self.n_inf = QSpinBox()
        self.n_inf.setRange(0, 20)
        self.n_inf.setValue(3)
        self.n_sup_i = QSpinBox()
        self.n_sup_i.setRange(0, 20)
        self.n_sup_i.setValue(2)
        self.n_sup_d = QSpinBox()
        self.n_sup_d.setRange(0, 20)
        self.n_sup_d.setValue(2)
        self.ramas = QSpinBox()
        self.ramas.setRange(2, 8)
        self.ramas.setValue(2)

        self.db_inf = QComboBox()
        self.db_sup_i = QComboBox()
        self.db_sup_d = QComboBox()
        self.db_inf.addItems(self._barras_combo_textos())
        self.db_sup_i.addItems(self._barras_combo_textos())
        self.db_sup_d.addItems(self._barras_combo_textos())
        self.db_inf.setCurrentText(self._valor_tentativo_diametro(16))
        self.db_sup_i.setCurrentText(self._valor_tentativo_diametro(16))
        self.db_sup_d.setCurrentText(self._valor_tentativo_diametro(16))

        self.sep_estribos = QLineEdit(self._valor_tentativo_longitud(150))

        layout_armado.addWidget(QLabel("Zona"), 0, 0)
        layout_armado.addWidget(QLabel("Cantidad"), 0, 1)
        layout_armado.addWidget(QLabel(f"Diametro ({self.unidad_diametro_barra})"), 0, 2)
        layout_armado.addWidget(QLabel("Inferior"), 1, 0)
        layout_armado.addWidget(self.n_inf, 1, 1)
        layout_armado.addWidget(self.db_inf, 1, 2)
        layout_armado.addWidget(QLabel("Superior izquierda"), 2, 0)
        layout_armado.addWidget(self.n_sup_i, 2, 1)
        layout_armado.addWidget(self.db_sup_i, 2, 2)
        layout_armado.addWidget(QLabel("Superior derecha"), 3, 0)
        layout_armado.addWidget(self.n_sup_d, 3, 1)
        layout_armado.addWidget(self.db_sup_d, 3, 2)
        layout_armado.addWidget(QLabel("Ramas de estribo"), 4, 0)
        layout_armado.addWidget(self.ramas, 4, 1)
        layout_armado.addWidget(QLabel(f"Separacion de estribos ({self.unidad_longitud})"), 5, 0)
        layout_armado.addWidget(self.sep_estribos, 5, 1, 1, 2)

        self.lbl_armado = QLabel("Armado actual / sugerido: pendiente de calculo")
        self.lbl_armado.setWordWrap(True)
        self.lbl_armado.setStyleSheet("padding: 6px; border: 1px solid gray;")
        layout_armado.addWidget(self.lbl_armado, 6, 0, 1, 3)

        grupo_armado.setLayout(layout_armado)
        fila_armado.addWidget(grupo_armado, 3)

        grupo_preview = QGroupBox("Vista previa de seccion")
        layout_preview = QVBoxLayout()
        self.figure_sec = Figure(figsize=(4.6, 4.0))
        self.canvas_sec = FigureCanvas(self.figure_sec)
        self.canvas_sec.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout_preview.addWidget(self.canvas_sec)
        grupo_preview.setLayout(layout_preview)
        fila_armado.addWidget(grupo_preview, 2)

        layout.addLayout(fila_armado)

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

    def _crear_tab_graficos(self):
        layout = QVBoxLayout(self.tab_graficos)
        self.lbl_guia_graficos = QLabel(
            "• Vista longitudinal con apoyos, luz y cargas.\n"
            "• Vista de seccion con armado y separacion libre."
        )
        self.lbl_guia_graficos.setWordWrap(True)
        self.lbl_guia_graficos.setFrameShape(QFrame.StyledPanel)
        self.lbl_guia_graficos.setStyleSheet("padding: 8px;")
        layout.addWidget(self.lbl_guia_graficos)

        self.figure_long = Figure(figsize=(8.5, 3.8))
        self.canvas_long = FigureCanvas(self.figure_long)
        layout.addWidget(self.canvas_long)

    def _actualizar_texto_unidades(self):
        norma = self._norma_actual()
        self.lbl_unidades.setText(
            f"Norma activa: {norma['nombre']}\n"
            f"Geometria: {self.unidad_longitud}\n"
            f"Recubrimientos: {self.unidad_recubrimiento}\n"
            f"Diametros: {self.unidad_diametro_barra}\n"
            f"Fuerzas: {self.unidad_fuerza}\n"
            f"Momentos y torsion: {self.unidad_momento}\n"
            f"Area de acero mostrada: {self.unidad_area_acero}\n"
            f"wu se interpreta como carga distribuida en {self.unidad_fuerza}/{self.unidad_longitud} y se convierte internamente a kN/m.\n"
            "Base interna del calculo: mm, MPa, kN, kN·m"
        )

    def _actualizar_modo(self):
        manual = self._tipo_modo_manual()
        self.n_inf.setEnabled(manual)
        self.db_inf.setEnabled(manual)
        self.n_sup_i.setEnabled(manual)
        self.db_sup_i.setEnabled(manual)
        self.n_sup_d.setEnabled(manual)
        self.db_sup_d.setEnabled(manual)
        self.ramas.setEnabled(manual)
        self.sep_estribos.setEnabled(manual)
        if manual:
            self.lbl_armado.setText("Modo verificacion: el calculo usa el armado ingresado.")
        else:
            self.lbl_armado.setText("Modo diseño: se estimara el acero requerido y se sugeriran barras.")

    def _conectar_actualizacion_croquis(self):
        widgets = [
            self.luz,
            self.bw,
            self.h,
            self.rec,
            self.dag,
            self.fc,
            self.fy,
            self.fyt,
            self.wu,
            self.puntual,
            self.x_p,
            self.mu_pos,
            self.mu_neg_i,
            self.mu_neg_d,
            self.vu_i,
            self.vu_d,
            self.tu,
            self.pu,
            self.sep_estribos,
        ]
        for widget in widgets:
            widget.textChanged.connect(self._actualizar_graficos_geometria)
        for combo in [self.db_estribo, self.db_inf, self.db_sup_i, self.db_sup_d, self.tipo_apoyo]:
            combo.currentTextChanged.connect(self._actualizar_graficos_geometria)
        for spin in [self.n_inf, self.n_sup_i, self.n_sup_d, self.ramas]:
            spin.valueChanged.connect(self._actualizar_graficos_geometria)

    def _conectar_entradas_recalculo(self):
        line_edits = [
            self.luz,
            self.bw,
            self.h,
            self.rec,
            self.dag,
            self.fc,
            self.fy,
            self.fyt,
            self.wu,
            self.puntual,
            self.x_p,
            self.mu_pos,
            self.mu_neg_i,
            self.mu_neg_d,
            self.vu_i,
            self.vu_d,
            self.tu,
            self.pu,
            self.sep_estribos,
        ]
        combos = [self.modo_viga, self.combo_norma, self.tipo_apoyo, self.db_estribo, self.db_inf, self.db_sup_i, self.db_sup_d]
        spins = [self.n_inf, self.n_sup_i, self.n_sup_d, self.ramas]

        for widget in line_edits:
            widget.textChanged.connect(self._marcar_resultados_como_desactualizados)
        for widget in combos:
            widget.currentTextChanged.connect(self._marcar_resultados_como_desactualizados)
        for widget in spins:
            widget.valueChanged.connect(self._marcar_resultados_como_desactualizados)

    def _marcar_resultados_como_desactualizados(self, *args):
        self._datos_modificados = True
        self.lbl_dirty.setText("Hay cambios sin recalcular.")

    def _leer_datos(self):
        return DatosViga(
            modo=self.modo_viga.currentText(),
            norma=self._norma_actual(),
            tipo_apoyo=self.tipo_apoyo.currentText(),
            luz_mm=self._longitud_a_mm(float(self.luz.text())),
            bw_mm=self._longitud_a_mm(float(self.bw.text())),
            h_mm=self._longitud_a_mm(float(self.h.text())),
            rec_mm=self._recubrimiento_a_mm(float(self.rec.text())),
            db_estribo_mm=self._diametro_a_mm(float(self.db_estribo.currentText())),
            dag_mm=self._longitud_a_mm(float(self.dag.text())),
            fc=float(self.fc.text()),
            fy=float(self.fy.text()),
            fyt=float(self.fyt.text()),
            wu_kN_m=carga_distribuida_a_kN_m(float(self.wu.text()), self.unidad_fuerza),
            P_kN=fuerza_a_kN(float(self.puntual.text()), self.unidad_fuerza),
            x_p_mm=self._longitud_a_mm(float(self.x_p.text())),
            Mu_pos_kNm=momento_a_kNm(float(self.mu_pos.text()), self.unidad_momento),
            Mu_neg_i_kNm=momento_a_kNm(float(self.mu_neg_i.text()), self.unidad_momento),
            Mu_neg_d_kNm=momento_a_kNm(float(self.mu_neg_d.text()), self.unidad_momento),
            Vu_i_kN=fuerza_a_kN(float(self.vu_i.text()), self.unidad_fuerza),
            Vu_d_kN=fuerza_a_kN(float(self.vu_d.text()), self.unidad_fuerza),
            Tu_kNm=momento_a_kNm(float(self.tu.text()), self.unidad_momento),
            Pu_kN=fuerza_a_kN(float(self.pu.text()), self.unidad_fuerza),
            n_inf=self.n_inf.value(),
            n_sup_i=self.n_sup_i.value(),
            n_sup_d=self.n_sup_d.value(),
            db_inf_mm=self._diametro_a_mm(float(self.db_inf.currentText())),
            db_sup_i_mm=self._diametro_a_mm(float(self.db_sup_i.currentText())),
            db_sup_d_mm=self._diametro_a_mm(float(self.db_sup_d.currentText())),
            ramas=self.ramas.value(),
            s_est_mm=self._longitud_a_mm(float(self.sep_estribos.text())),
        )

    def _validar_datos_basicos(self, datos: DatosViga):
        if datos.bw_mm <= 0:
            raise ValueError("bw debe ser mayor que cero.")
        if datos.h_mm <= 0:
            raise ValueError("h debe ser mayor que cero.")
        if datos.luz_mm <= 0:
            raise ValueError("La luz debe ser mayor que cero.")
        if datos.rec_mm < 0:
            raise ValueError("El recubrimiento no puede ser negativo.")
        if datos.fc <= 0 or datos.fy <= 0 or datos.fyt <= 0:
            raise ValueError("f'c, fy y fyt deben ser mayores que cero.")
        if self._tipo_modo_manual() and datos.s_est_mm <= 0:
            raise ValueError("La separacion de estribos debe ser mayor que cero en modo manual.")

    # ======================================================
    # GRAFICOS
    # ======================================================
    def _actualizar_graficos_geometria(self):
        try:
            datos = self._leer_datos()
            self._graficar_seccion(datos)
            self._graficar_longitudinal(datos)
        except Exception as e:
            print(f"Error actualizando graficos de viga: {e}")

    def _graficar_longitudinal(self, datos: DatosViga):
        self.figure_long.clear()
        ax = self.figure_long.add_subplot(111)

        L = datos.luz_mm
        x_p = min(max(datos.x_p_mm, 0.0), L)

        ax.plot([0, L], [0, 0], linewidth=3.0, color="black")
        ax.scatter([0, L], [0, 0], marker="^", s=160, color="dimgray")

        if datos.wu_kN_m > 0:
            xs = np.linspace(0, L, 12)
            for x_val in xs:
                ax.arrow(x_val, 220, 0, -160, head_width=70, head_length=35, fc="steelblue", ec="steelblue")
            ax.text(L * 0.5, 250, f"wu={datos.wu_kN_m:.2f} kN/m", ha="center", color="steelblue")

        if datos.P_kN > 0:
            ax.arrow(x_p, 320, 0, -220, head_width=90, head_length=40, fc="firebrick", ec="firebrick")
            ax.text(x_p, 355, f"P={datos.P_kN:.2f} kN\nx={self._mm_a_longitud_usuario(x_p):.2f} {self.unidad_longitud}", ha="center")

        ax.text(0, -110, f"Vu izq={datos.Vu_i_kN:.2f} kN", ha="left")
        ax.text(L, -110, f"Vu der={datos.Vu_d_kN:.2f} kN", ha="right")
        ax.text(L * 0.5, -180, f"Mu+={datos.Mu_pos_kNm:.2f} kN·m", ha="center")
        ax.text(0, -255, f"Mu- izq={datos.Mu_neg_i_kNm:.2f} kN·m", ha="left")
        ax.text(L, -255, f"Mu- der={datos.Mu_neg_d_kNm:.2f} kN·m", ha="right")
        ax.text(L * 0.02, 390, f"Pu axial real={datos.Pu_kN:.2f} kN", ha="left")
        ax.text(L * 0.62, 390, f"Tu={datos.Tu_kNm:.2f} kN·m", ha="left")

        ax.set_title("Vista longitudinal de la viga")
        ax.set_xlim(-0.08 * max(L, 1.0), 1.08 * max(L, 1.0))
        ax.set_ylim(-350, 420)
        ax.set_xlabel(f"Luz ({self.unidad_longitud})")
        ax.set_yticks([])
        ax.grid(True, axis="x", alpha=0.25)
        self.canvas_long.draw()

    def _graficar_seccion(self, datos: DatosViga):
        self.figure_sec.clear()
        ax = self.figure_sec.add_subplot(111)

        bw = datos.bw_mm
        h = datos.h_mm
        rec = datos.rec_mm
        d_est = datos.db_estribo_mm

        ax.plot([0, bw, bw, 0, 0], [0, 0, h, h, 0], linewidth=1.7, color="black")

        x_int0 = rec + d_est
        x_int1 = bw - (rec + d_est)
        y_top = h - (rec + d_est)
        y_bot = rec + d_est
        ax.plot([x_int0, x_int1, x_int1, x_int0, x_int0], [y_bot, y_bot, y_top, y_top, y_bot], linestyle="--", color="gray")

        conjuntos = [
            (self._posiciones_barras_horizontal(bw, rec, d_est, datos.n_inf, datos.db_inf_mm), y_bot),
            (self._posiciones_barras_horizontal(bw, rec, d_est, datos.n_sup_i, datos.db_sup_i_mm), y_top),
            (self._posiciones_barras_horizontal(bw, rec, d_est, datos.n_sup_d, datos.db_sup_d_mm), y_top - 35.0),
        ]
        for posiciones, y_val in conjuntos:
            for x_val, dbar in posiciones:
                ax.scatter(x_val, y_val, s=max(35, dbar * 2.5), color="firebrick")

        ax.set_title("Vista de seccion transversal")
        ax.set_aspect("equal", adjustable="box")
        ax.set_xlim(-0.12 * bw, 1.12 * bw)
        ax.set_ylim(-0.12 * h, 1.12 * h)
        ax.grid(True, alpha=0.25)
        ax.set_xlabel("x (mm)")
        ax.set_ylabel("y (mm)")
        self.canvas_sec.draw()

    def _posiciones_barras_horizontal(self, bw, rec, d_est, n_barras, dbar):
        if n_barras <= 0 or dbar <= 0:
            return []
        x0 = rec + d_est + dbar / 2.0
        x1 = bw - (rec + d_est + dbar / 2.0)
        if n_barras == 1:
            return [((x0 + x1) / 2.0, dbar)]
        if x1 <= x0:
            return []
        xs = np.linspace(x0, x1, n_barras)
        return [(float(x), dbar) for x in xs]

    # ======================================================
    # CALCULO
    # ======================================================
    def _actualizar_resumen_armado(self, datos: DatosViga, resultado):
        texto = generar_texto_armado(
            datos,
            resultado,
            self.unidad_area_acero,
            self.unidad_longitud,
            self._diametros_disponibles_mm(),
            self.db_inf.currentText(),
            self.db_sup_i.currentText(),
            self.db_sup_d.currentText(),
            self.db_estribo.currentText(),
            self._mm_a_longitud_usuario,
        )
        self.lbl_armado.setText(texto)

    def _guardar_ultimo_resultado(self, datos: DatosViga, resultado):
        self.ultimo_resultado = {
            "modo_viga": datos.modo,
            "norma": datos.norma["nombre"],
            "cumple": resultado.cumple_global,
            "diagnostico": resultado.diagnostico_categoria,
            "resumen_texto": self.resultados_texto.toPlainText(),
            "comprobaciones_texto": self.texto_comprobaciones.toPlainText(),
        }

    def calcular(self):
        try:
            self.resultados_texto.clear()
            self.texto_comprobaciones.clear()

            datos = self._leer_datos()
            self._validar_datos_basicos(datos)
            resultado = calcular_viga(datos)

            self.texto_comprobaciones.setPlainText(generar_texto_comprobaciones(resultado))
            self.resultados_texto.setPlainText(
                generar_texto_resultados(
                    datos,
                    resultado,
                    self.unidad_area_acero,
                    self._diametros_disponibles_mm(),
                    self.unidad_longitud,
                    self.db_estribo.currentText(),
                )
            )
            self._actualizar_resumen_armado(datos, resultado)
            self._guardar_ultimo_resultado(datos, resultado)

            self._datos_modificados = False
            self.lbl_dirty.setText("")
            self._actualizar_graficos_geometria()

        except Exception as e:
            QMessageBox.warning(self, "Error de datos", f"Revisa los valores ingresados.\n\n{e}")

    # ======================================================
    # LIMPIEZA / GUARDADO
    # ======================================================
    def limpiar(self):
        self.ultimo_resultado = {}
        self.ultimo_grafico = {}

        self.modo_viga.setCurrentIndex(0)
        self.combo_norma.setCurrentIndex(0)
        self.tipo_apoyo.setCurrentText("Simplemente apoyada")
        self.luz.setText(self._valor_tentativo_longitud(6000))
        self.bw.setText(self._valor_tentativo_longitud(250))
        self.h.setText(self._valor_tentativo_longitud(500))
        self.rec.setText(self._valor_tentativo_recubrimiento(30))
        self.db_estribo.setCurrentText(self._valor_tentativo_diametro(8))
        self.dag.setText(self._valor_tentativo_longitud(19))
        self.fc.setText("28")
        self.fy.setText("420")
        self.fyt.setText("420")
        self.wu.setText("22")
        self.puntual.setText("0")
        self.x_p.setText(self._valor_tentativo_longitud(3000))
        self.mu_pos.setText("120")
        self.mu_neg_i.setText("80")
        self.mu_neg_d.setText("80")
        self.vu_i.setText("95")
        self.vu_d.setText("95")
        self.tu.setText("0")
        self.pu.setText("0")
        self.n_inf.setValue(3)
        self.n_sup_i.setValue(2)
        self.n_sup_d.setValue(2)
        self.db_inf.setCurrentText(self._valor_tentativo_diametro(16))
        self.db_sup_i.setCurrentText(self._valor_tentativo_diametro(16))
        self.db_sup_d.setCurrentText(self._valor_tentativo_diametro(16))
        self.ramas.setValue(2)
        self.sep_estribos.setText(self._valor_tentativo_longitud(150))

        self.resultados_texto.clear()
        self.texto_comprobaciones.clear()
        self.lbl_armado.setText("Armado actual / sugerido: pendiente de calculo")
        self._actualizar_modo()
        self._actualizar_graficos_geometria()
        self._datos_modificados = False
        self.lbl_dirty.setText("")

    def guardar(self):
        if not self.ultimo_resultado:
            QMessageBox.information(self, "Aviso", "Primero debes calcular.")
            return
        guardar_resultado("vigas", self.ultimo_resultado)
        QMessageBox.information(self, "Guardado", "Resultados de vigas guardados correctamente.")
