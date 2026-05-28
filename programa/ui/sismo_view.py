from __future__ import annotations

from datetime import datetime
from io import BytesIO
from pathlib import Path

import numpy as np
import pandas as pd
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QInputDialog,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

try:
    from PySide6.QtCore import QUrl
    from PySide6.QtPdf import QPdfDocument
    from PySide6.QtPdfWidgets import QPdfView
    PDF_VIEW_AVAILABLE = True
except Exception:
    QUrl = None
    QPdfDocument = None
    QPdfView = None
    PDF_VIEW_AVAILABLE = False


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
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MAP_PDF = PROJECT_ROOT / "assets" / "normativa" / "NORMA-BOLIVIANA-DE-DISENO-SISMICO-2023.pdf"


class SismoView(QWidget):
    def __init__(self):
        super().__init__()

        self.spectrum_df = pd.DataFrame()
        self.results = {}
        self.inputs = {}
        self.fig = Figure(figsize=(8.8, 5.1))
        self.canvas = FigureCanvas(self.fig)

        layout = QVBoxLayout(self)

        title = QLabel("MODULO SISMO - ESPECTRO SISMICO NBDS 2023")
        title.setStyleSheet("font-size: 16px; font-weight: bold; padding: 4px;")
        layout.addWidget(title)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self.tab_inputs = QWidget()
        self.tab_results = QWidget()
        self.tab_table = QWidget()
        self.tab_plot = QWidget()
        self.tab_pdf = QWidget()

        self.tabs.addTab(self.tab_inputs, "Datos de entrada")
        self.tabs.addTab(self.tab_results, "Resultados")
        self.tabs.addTab(self.tab_table, "Tabla del espectro")
        self.tabs.addTab(self.tab_plot, "Grafica del espectro")
        self.tabs.addTab(self.tab_pdf, "Reporte PDF")

        self._build_inputs_tab()
        self._build_results_tab()
        self._build_table_tab()
        self._build_plot_tab()
        self._build_pdf_tab()
        self._update_visibility()

    # ======================================================
    # UI
    # ======================================================
    def _build_inputs_tab(self):
        outer = QVBoxLayout(self.tab_inputs)
        splitter = QSplitter(Qt.Horizontal)
        outer.addWidget(splitter)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        left_layout.addWidget(scroll)

        container = QWidget()
        scroll.setWidget(container)
        layout = QVBoxLayout(container)

        project_group = QGroupBox("Datos del proyecto")
        project_form = QFormLayout()
        self.project_name = QLineEdit()
        self.location = QLineEdit()
        self.responsible = QLineEdit()
        project_form.addRow("Nombre del proyecto", self.project_name)
        project_form.addRow("Ubicacion", self.location)
        project_form.addRow("Responsable", self.responsible)
        project_group.setLayout(project_form)
        layout.addWidget(project_group)

        basic_group = QGroupBox("Datos sismicos basicos")
        basic_form = QFormLayout()
        self.pga_help = QLabel(
            "PGA_S0 no se calcula con la tabla de suelo. Es un dato de amenaza sismica del sitio "
            "que se toma del mapa de la NBDS 2023 y se ingresa como fraccion de g."
        )
        self.pga_help.setWordWrap(True)
        self.pga_help.setStyleSheet("color: #2f4f4f;")
        self.pga_input = QLineEdit("0.160")
        self.pga_input.setPlaceholderText("Ejemplo: 0.16")
        self.pga_input.textChanged.connect(self._update_visibility)
        self.structure_combo = QComboBox()
        self.structure_combo.addItems(list(STRUCTURE_TYPES.keys()))
        self.structure_combo.currentTextChanged.connect(self._update_visibility)
        basic_form.addRow("", self.pga_help)
        basic_form.addRow("PGA_S0 del mapa de amenaza (fraccion de g)", self.pga_input)
        basic_form.addRow("Tipo de estructura", self.structure_combo)
        basic_group.setLayout(basic_form)
        layout.addWidget(basic_group)

        ffv_group = QGroupBox("Coeficientes de sitio Fa y Fv")
        ffv_form = QFormLayout()
        self.ffv_method_combo = QComboBox()
        self.ffv_method_combo.addItems(["Automatico segun NBDS 2023", "Manual / avanzado"])
        self.ffv_method_combo.currentTextChanged.connect(self._update_visibility)
        self.soil_combo = QComboBox()
        self.soil_combo.addItems([
            "S0 - Roca dura",
            "S1 - Roca",
            "S2 - Suelo muy rigido o roca blanda",
            "S3 - Suelo rigido",
            "S4 - Suelo blando",
            "S5 - Requiere analisis especial de respuesta de sitio",
        ])
        self.soil_combo.currentTextChanged.connect(self._update_visibility)
        self.ffv_message = QLabel("")
        self.ffv_message.setWordWrap(True)
        self.ffv_message.setStyleSheet("color: #8a3a00; font-weight: bold;")
        self.soil_help = QLabel(
            "El tipo de suelo S0, S1, S2, S3, S4 o S5 no es la aceleracion PGA_S0. "
            "El suelo solo define como se obtienen Fa y Fv."
        )
        self.soil_help.setWordWrap(True)
        self.soil_help.setStyleSheet("color: #2f4f4f;")
        self.fa_display = QLineEdit()
        self.fa_display.setReadOnly(True)
        self.fv_display = QLineEdit()
        self.fv_display.setReadOnly(True)
        self.fa_manual = QLineEdit("1.00000")
        self.fv_manual = QLineEdit("1.00000")
        self.fa_manual.textChanged.connect(self._update_visibility)
        self.fv_manual.textChanged.connect(self._update_visibility)
        ffv_form.addRow("Metodo para Fa y Fv", self.ffv_method_combo)
        ffv_form.addRow("Tipo de suelo", self.soil_combo)
        ffv_form.addRow("", self.soil_help)
        ffv_form.addRow("", self.ffv_message)
        ffv_form.addRow("Fa calculado", self.fa_display)
        ffv_form.addRow("Fv calculado", self.fv_display)
        ffv_form.addRow("Fa manual", self.fa_manual)
        ffv_form.addRow("Fv manual", self.fv_manual)
        ffv_group.setLayout(ffv_form)
        layout.addWidget(ffv_group)

        importance_group = QGroupBox("Factor de importancia")
        importance_form = QFormLayout()
        self.ie_manual = QLineEdit("1.00000")
        importance_form.addRow("Ie manual (solo Tipo I)", self.ie_manual)
        importance_group.setLayout(importance_form)
        layout.addWidget(importance_group)

        period_group = QGroupBox("Periodos caracteristicos calculados automaticamente")
        period_form = QFormLayout()
        self.period_message = QLabel(
            "T0, Ts y TL se calculan automaticamente con las formulas de la norma a partir de Fa y Fv. "
            "No se ingresan manualmente ni se toman de una tabla fija."
        )
        self.period_message.setWordWrap(True)
        self.t0_display = QLineEdit()
        self.t0_display.setReadOnly(True)
        self.ts_display = QLineEdit()
        self.ts_display.setReadOnly(True)
        self.tl_display = QLineEdit()
        self.tl_display.setReadOnly(True)
        period_form.addRow("", self.period_message)
        period_form.addRow("T0 calculado (s)", self.t0_display)
        period_form.addRow("Ts calculado (s)", self.ts_display)
        period_form.addRow("TL calculado (s)", self.tl_display)
        period_group.setLayout(period_form)
        layout.addWidget(period_group)

        system_group = QGroupBox("Sistema estructural")
        system_form = QFormLayout()
        self.system_combo = QComboBox()
        self.system_combo.addItems(list(STRUCTURAL_SYSTEMS.keys()))
        self.system_combo.currentTextChanged.connect(self._update_visibility)
        self.r_manual = QLineEdit("5.00000")
        self.cd_manual = QLineEdit("4.50000")
        self.deriva_manual = QLineEdit("0.01000")
        system_form.addRow("Sistema estructural", self.system_combo)
        system_form.addRow("R manual", self.r_manual)
        system_form.addRow("Cd manual", self.cd_manual)
        system_form.addRow("Deriva maxima manual", self.deriva_manual)
        system_group.setLayout(system_form)
        layout.addWidget(system_group)

        tau_group = QGroupBox("Factor topografico tau")
        tau_form = QFormLayout()
        self.tau_mode = QComboBox()
        self.tau_mode.addItems([
            "Sin efecto topografico: tau = 1.00",
            "Ingresar tau manualmente",
            "Calcular tau por pendiente",
        ])
        self.tau_mode.currentTextChanged.connect(self._update_visibility)
        self.tau_manual = QLineEdit("1.00000")
        self.H_input = QLineEdit("20.00")
        self.I_input = QLineEdit("0.60")
        self.i_input = QLineEdit("0.10")
        tau_form.addRow("Selector de tau", self.tau_mode)
        tau_form.addRow("tau manual", self.tau_manual)
        tau_form.addRow("H (m)", self.H_input)
        tau_form.addRow("I pendiente cuesta abajo", self.I_input)
        tau_form.addRow("i pendiente cuesta arriba", self.i_input)
        tau_group.setLayout(tau_form)
        layout.addWidget(tau_group)

        range_group = QGroupBox("Rango de grafica y tabla")
        range_form = QFormLayout()
        self.tmin_input = QLineEdit("0.0000")
        self.tmax_input = QLineEdit("5.0000")
        self.dt_input = QLineEdit("0.0100")
        self.range_message = QLabel(
            "Estos valores solo controlan el intervalo de calculo de la tabla y la grafica. No reemplazan T0, Ts ni TL."
        )
        self.range_message.setWordWrap(True)
        range_form.addRow("", self.range_message)
        range_form.addRow("Tmin (s)", self.tmin_input)
        range_form.addRow("Tmax (s)", self.tmax_input)
        range_form.addRow("dT (s)", self.dt_input)
        range_group.setLayout(range_form)
        layout.addWidget(range_group)

        buttons = QHBoxLayout()
        self.calculate_button = QPushButton("Calcular espectro")
        self.calculate_button.clicked.connect(self.calculate)
        self.clear_button = QPushButton("Limpiar")
        self.clear_button.clicked.connect(self._reset_defaults)
        buttons.addWidget(self.calculate_button)
        buttons.addWidget(self.clear_button)
        layout.addLayout(buttons)
        layout.addStretch()

        splitter.addWidget(left_panel)
        splitter.addWidget(self._build_map_panel())
        splitter.setSizes([700, 500])

    def _build_map_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)

        title = QLabel("Mapa de apoyo para seleccionar PGA_S0")
        title.setStyleSheet("font-weight: bold;")
        layout.addWidget(title)

        help_label = QLabel(
            "Aqui puedes revisar el PDF de la norma guardado dentro del proyecto y acercarte al mapa de amenaza. "
            "El visor es de apoyo para que el usuario estime el valor de PGA_S0 sin salir del programa."
        )
        help_label.setWordWrap(True)
        layout.addWidget(help_label)

        controls = QGridLayout()
        self.map_page_label = QLabel("Pagina: -")
        self.map_zoom_label = QLabel("Zoom: 100%")
        self.map_prev_button = QPushButton("Pagina anterior")
        self.map_next_button = QPushButton("Pagina siguiente")
        self.map_zoom_in_button = QPushButton("Zoom +")
        self.map_zoom_out_button = QPushButton("Zoom -")
        self.map_fit_button = QPushButton("Ajustar ancho")
        self.map_page_button = QPushButton("Ir a pagina")
        self.map_open_button = QPushButton("Abrir PDF completo")

        self.map_prev_button.clicked.connect(lambda: self._change_pdf_page(-1))
        self.map_next_button.clicked.connect(lambda: self._change_pdf_page(1))
        self.map_zoom_in_button.clicked.connect(lambda: self._change_pdf_zoom(1.2))
        self.map_zoom_out_button.clicked.connect(lambda: self._change_pdf_zoom(1 / 1.2))
        self.map_fit_button.clicked.connect(self._fit_pdf_width)
        self.map_page_button.clicked.connect(self._ask_pdf_page)
        self.map_open_button.clicked.connect(self._open_map_pdf_external)

        controls.addWidget(self.map_prev_button, 0, 0)
        controls.addWidget(self.map_next_button, 0, 1)
        controls.addWidget(self.map_zoom_out_button, 1, 0)
        controls.addWidget(self.map_zoom_in_button, 1, 1)
        controls.addWidget(self.map_fit_button, 2, 0)
        controls.addWidget(self.map_page_button, 2, 1)
        controls.addWidget(self.map_page_label, 3, 0)
        controls.addWidget(self.map_zoom_label, 3, 1)
        layout.addLayout(controls)
        layout.addWidget(self.map_open_button)

        self.map_status_label = QLabel("")
        self.map_status_label.setWordWrap(True)
        layout.addWidget(self.map_status_label)

        if PDF_VIEW_AVAILABLE:
            self.pdf_document = QPdfDocument(self)
            self.pdf_view = QPdfView()
            self.pdf_view.setDocument(self.pdf_document)
            self.pdf_view.setZoomMode(QPdfView.ZoomMode.Custom)
            self.current_zoom_factor = 1.0
            self.current_pdf_page = 0
            layout.addWidget(self.pdf_view, 1)
            self._load_default_map_pdf()
        else:
            self.pdf_document = None
            self.pdf_view = None
            self.current_zoom_factor = 1.0
            self.current_pdf_page = 0
            fallback = QLabel(
                "El visor PDF embebido no esta disponible en esta instalacion de PySide6. "
                "Puedes abrir el PDF completo con el boton de abajo."
            )
            fallback.setWordWrap(True)
            layout.addWidget(fallback, 1)
            self._update_pdf_ui_state()

        return panel

    def _build_results_tab(self):
        layout = QVBoxLayout(self.tab_results)

        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        layout.addWidget(self.summary_text)

        self.control_table = QTableWidget(0, 2)
        self.control_table.setHorizontalHeaderLabels(["Parametro", "Valor"])
        self.control_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.control_table)

        self.concept_table = QTableWidget(0, 5)
        self.concept_table.setHorizontalHeaderLabels(["Parametro", "Valor", "Concepto", "Justificacion", "Metodo"])
        self.concept_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.concept_table)

    def _build_table_tab(self):
        layout = QVBoxLayout(self.tab_table)

        self.spectrum_table = QTableWidget(0, 3)
        self.spectrum_table.setHorizontalHeaderLabels(["T_s", "Sae_elastico_g", "Sa_diseno_g"])
        self.spectrum_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.spectrum_table)

        buttons = QHBoxLayout()
        self.csv_button = QPushButton("Descargar CSV")
        self.csv_button.clicked.connect(lambda: self._export_table("csv"))
        self.xlsx_button = QPushButton("Descargar Excel XLSX")
        self.xlsx_button.clicked.connect(lambda: self._export_table("xlsx"))
        self.txt_button = QPushButton("Descargar TXT")
        self.txt_button.clicked.connect(lambda: self._export_table("txt"))
        buttons.addWidget(self.csv_button)
        buttons.addWidget(self.xlsx_button)
        buttons.addWidget(self.txt_button)
        layout.addLayout(buttons)

    def _build_plot_tab(self):
        layout = QVBoxLayout(self.tab_plot)
        self.plot_info = QLabel("La grafica del espectro se mostrara aqui despues del calculo.")
        self.plot_info.setWordWrap(True)
        layout.addWidget(self.plot_info)
        layout.addWidget(self.canvas)

        self.png_button = QPushButton("Descargar grafica PNG")
        self.png_button.clicked.connect(self._export_plot_png)
        layout.addWidget(self.png_button)

    def _build_pdf_tab(self):
        layout = QVBoxLayout(self.tab_pdf)
        self.pdf_info = QTextEdit()
        self.pdf_info.setReadOnly(True)
        self.pdf_info.setPlainText(
            "El reporte PDF incluira:\n"
            "- Datos del proyecto\n"
            "- Tablas Fa y Fv usadas\n"
            "- Detalle tecnico de interpolacion\n"
            "- Desarrollo numerico de formulas\n"
            "- Tabla de control del espectro\n"
            "- Grafica con Sae y Sa\n"
            "- Tabla reducida del espectro\n"
            "- Advertencias normativas"
        )
        layout.addWidget(self.pdf_info)

        self.pdf_button = QPushButton("Generar reporte PDF")
        self.pdf_button.clicked.connect(self._export_pdf)
        layout.addWidget(self.pdf_button)
        layout.addStretch()

    # ======================================================
    # HELPERS
    # ======================================================
    def _soil_class(self):
        return self.soil_combo.currentText().split(" - ")[0]

    def _float(self, widget: QLineEdit) -> float:
        return float(widget.text().strip())

    def _set_readonly_value(self, widget: QLineEdit, value):
        widget.setText("" if value is None else f"{value:.5f}")

    def _clear_period_displays(self):
        self.t0_display.setText("")
        self.ts_display.setText("")
        self.tl_display.setText("")

    def _update_period_previews(self, fa, fv):
        if fa is None or fv is None or fa <= 0 or fv <= 0:
            self._clear_period_displays()
            return
        t0, ts, tl = self.calculate_characteristic_periods(fa, fv)
        self._set_readonly_value(self.t0_display, t0)
        self._set_readonly_value(self.ts_display, ts)
        self._set_readonly_value(self.tl_display, tl)

    def _update_visibility(self):
        soil_class = self._soil_class()
        ffv_mode = self.ffv_method_combo.currentText()

        auto_mode = ffv_mode == "Automatico segun NBDS 2023" and soil_class != "S5"
        s5_mode = ffv_mode == "Automatico segun NBDS 2023" and soil_class == "S5"
        manual_mode = ffv_mode == "Manual / avanzado"

        self.fa_display.setVisible(auto_mode)
        self.fv_display.setVisible(auto_mode)
        self.fa_manual.setVisible(s5_mode or manual_mode)
        self.fv_manual.setVisible(s5_mode or manual_mode)

        if auto_mode:
            pga_text = self.pga_input.text().strip()
            try:
                pga_s0 = float(pga_text)
                if 0 < pga_s0 <= 1:
                    fa = self.get_fa(pga_s0, soil_class)
                    fv = self.get_fv(pga_s0, soil_class)
                    self._set_readonly_value(self.fa_display, fa)
                    self._set_readonly_value(self.fv_display, fv)
                    self._update_period_previews(fa, fv)
                else:
                    self.fa_display.setText("")
                    self.fv_display.setText("")
                    self._clear_period_displays()
            except ValueError:
                self.fa_display.setText("")
                self.fv_display.setText("")
                self._clear_period_displays()
            self.ffv_message.setText(
                "Fa y Fv calculados automaticamente segun tablas NBDS 2023 e interpolacion lineal."
            )
        elif s5_mode:
            self.fa_display.setText("")
            self.fv_display.setText("")
            try:
                self._update_period_previews(float(self.fa_manual.text().strip()), float(self.fv_manual.text().strip()))
            except ValueError:
                self._clear_period_displays()
            self.ffv_message.setText(
                "El suelo S5 requiere analisis especial de respuesta de sitio. Ingrese Fa y Fv manualmente segun estudio geotecnico/sismico."
            )
        else:
            self.fa_display.setText("")
            self.fv_display.setText("")
            try:
                self._update_period_previews(float(self.fa_manual.text().strip()), float(self.fv_manual.text().strip()))
            except ValueError:
                self._clear_period_displays()
            self.ffv_message.setText(
                "Modo manual activado. Verifique que los valores ingresados correspondan a un estudio tecnico o criterio profesional."
            )

        manual_ie = STRUCTURE_TYPES[self.structure_combo.currentText()]["ie"] is None
        self.ie_manual.setVisible(manual_ie)

        manual_system = self.system_combo.currentText() == "Manual"
        self.r_manual.setVisible(manual_system)
        self.cd_manual.setVisible(manual_system)
        self.deriva_manual.setVisible(manual_system)

        tau_mode = self.tau_mode.currentText()
        manual_tau = tau_mode == "Ingresar tau manualmente"
        slope_tau = tau_mode == "Calcular tau por pendiente"
        self.tau_manual.setVisible(manual_tau)
        self.H_input.setVisible(slope_tau)
        self.I_input.setVisible(slope_tau)
        self.i_input.setVisible(slope_tau)

    def _reset_defaults(self):
        self.project_name.setText("")
        self.location.setText("")
        self.responsible.setText("")
        self.pga_input.setText("0.160")
        self.structure_combo.setCurrentText("Tipo II - Edificaciones comunes")
        self.ffv_method_combo.setCurrentText("Automatico segun NBDS 2023")
        self.soil_combo.setCurrentText("S0 - Roca dura")
        self.fa_manual.setText("1.00000")
        self.fv_manual.setText("1.00000")
        self.ie_manual.setText("1.00000")
        self.system_combo.setCurrentText("Porticos especiales de hormigon armado")
        self.r_manual.setText("5.00000")
        self.cd_manual.setText("4.50000")
        self.deriva_manual.setText("0.01000")
        self.tau_mode.setCurrentText("Sin efecto topografico: tau = 1.00")
        self.tau_manual.setText("1.00000")
        self.H_input.setText("20.00")
        self.I_input.setText("0.60")
        self.i_input.setText("0.10")
        self.tmin_input.setText("0.0000")
        self.tmax_input.setText("5.0000")
        self.dt_input.setText("0.0100")
        self.summary_text.clear()
        self.control_table.setRowCount(0)
        self.concept_table.setRowCount(0)
        self.spectrum_table.setRowCount(0)
        self.spectrum_df = pd.DataFrame()
        self.results = {}
        self.inputs = {}
        self.fig.clear()
        self.canvas.draw()
        self._update_visibility()
        self._update_pdf_ui_state()

    # ======================================================
    # CALCULO
    # ======================================================
    def interpolate_table_value(self, x, x_values, y_values):
        if x <= x_values[0]:
            return float(y_values[0])
        if x >= x_values[-1]:
            return float(y_values[-1])
        for i in range(len(x_values) - 1):
            x1 = x_values[i]
            x2 = x_values[i + 1]
            y1 = y_values[i]
            y2 = y_values[i + 1]
            if x1 <= x <= x2:
                return float(y1 + (y2 - y1) * (x - x1) / (x2 - x1))
        return float(y_values[-1])

    def get_interpolation_detail(self, x, x_values, y_values):
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

    def get_fa(self, pga_s0, soil_class):
        if soil_class == "S5":
            return None
        return self.interpolate_table_value(pga_s0, FA_X, FA_TABLE[soil_class])

    def get_fv(self, pga_s0, soil_class):
        if soil_class == "S5":
            return None
        return self.interpolate_table_value(pga_s0, FV_X, FV_TABLE[soil_class])

    def get_fa_detail(self, pga_s0, soil_class):
        if soil_class == "S5":
            return None
        return self.get_interpolation_detail(pga_s0, FA_X, FA_TABLE[soil_class])

    def get_fv_detail(self, pga_s0, soil_class):
        if soil_class == "S5":
            return None
        return self.get_interpolation_detail(pga_s0, FV_X, FV_TABLE[soil_class])

    def get_importance_factor(self, structure_type, ie_manual=None):
        info = STRUCTURE_TYPES[structure_type]
        if info["ie"] is not None:
            return float(info["ie"]), "Se asigno segun el tipo de estructura seleccionado."
        return float(ie_manual), "El usuario ingreso manualmente el factor de importancia para Tipo I."

    def get_structural_system_values(self, system_name, manual_r=None, manual_cd=None, manual_deriva=None):
        info = STRUCTURAL_SYSTEMS[system_name]
        if info["R"] is not None:
            return float(info["R"]), float(info["Cd"]), float(info["deriva_max"]), "Se asignaron segun el sistema estructural seleccionado."
        return float(manual_r), float(manual_cd), float(manual_deriva), "El usuario ingreso manualmente R, Cd y deriva maxima."

    def calculate_topographic_factor(self, mode, tau_manual=None, H=None, I=None, i=None):
        if mode == "Sin efecto topografico: tau = 1.00":
            return 1.0, {"justification": "No se considero amplificacion topografica especial.", "a": None, "b": None, "c": None}

        if mode == "Ingresar tau manualmente":
            return float(tau_manual), {"justification": "El usuario ingreso manualmente el factor topografico.", "a": None, "b": None, "c": None}

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
            elif diferencia <= 0.90:
                tau = 1.0 + 0.80 * (diferencia - 0.40)
            else:
                tau = 1.40

        return float(tau), {"justification": "Se calculo a partir de las pendientes y altura del relieve.", "a": a, "b": b, "c": c}

    def _cds_by_fa(self, value, structure_code):
        if structure_code == "IV":
            if value < 0.067:
                return "A"
            if value < 0.133:
                return "C"
            return "D"
        if value < 0.067:
            return "A"
        if value < 0.133:
            return "B"
        if value < 0.200:
            return "C"
        return "D"

    def _cds_by_fv(self, value, structure_code):
        if structure_code == "IV":
            if value < 0.054:
                return "A"
            if value < 0.106:
                return "C"
            return "D"
        if value < 0.054:
            return "A"
        if value < 0.106:
            return "B"
        if value < 0.160:
            return "C"
        return "D"

    def calculate_cds(self, pga_s0, fa, fv, structure_code):
        fas0 = fa * pga_s0
        fvs0 = fv * pga_s0
        cds_fa = self._cds_by_fa(fas0, structure_code)
        cds_fv = self._cds_by_fv(fvs0, structure_code)
        cds_final = cds_fa if CDS_ORDER[cds_fa] >= CDS_ORDER[cds_fv] else cds_fv
        if structure_code in {"I", "II", "III"} and pga_s0 >= 0.330:
            cds_final = "E"
        if structure_code == "IV" and pga_s0 >= 0.330:
            cds_final = "F"
        return cds_fa, cds_fv, cds_final, fas0, fvs0

    def calculate_characteristic_periods(self, fa, fv):
        return 0.15 * fv / fa, 0.50 * fv / fa, 4.00 * fv / fa

    def calculate_sae(self, periods, pga_s0, fa, fv, t0, ts, tl):
        periods = np.asarray(periods, dtype=float)
        sae = np.zeros_like(periods, dtype=float)
        mask1 = periods < t0
        mask2 = (periods >= t0) & (periods <= ts)
        mask3 = (periods > ts) & (periods <= tl)
        mask4 = periods > tl
        sae[mask1] = fa * pga_s0 * (1.0 + 1.5 * periods[mask1] / t0)
        sae[mask2] = 2.5 * fa * pga_s0
        sae[mask3] = 1.25 * fv * pga_s0 / periods[mask3]
        sae[mask4] = 1.25 * fv * pga_s0 * tl / (periods[mask4] ** 2)
        return sae

    def _sae_at_period(self, period, pga_s0, fa, fv, t0, ts, tl):
        return float(self.calculate_sae(np.array([period], dtype=float), pga_s0, fa, fv, t0, ts, tl)[0])

    def calculate_spectrum(self, pga_s0, fa, fv, ie, tau, r_value, tmin, tmax, dt):
        if pga_s0 <= 0:
            raise ValueError("PGA_S0 debe ser mayor que cero.")
        if pga_s0 > 1:
            raise ValueError("PGA_S0 debe ingresarse como fraccion de g. Ejemplo: 0.16, no 16.")
        if fa <= 0 or fv <= 0:
            raise ValueError("Fa y Fv deben ser mayores que cero.")
        if r_value <= 0:
            raise ValueError("R debe ser mayor que cero.")
        if tmax <= tmin:
            raise ValueError("Tmax debe ser mayor que Tmin.")
        if dt <= 0:
            raise ValueError("dT debe ser mayor que cero.")

        t0, ts, tl = self.calculate_characteristic_periods(fa, fv)
        periods = np.arange(tmin, tmax + dt, dt)
        sae = self.calculate_sae(periods, pga_s0, fa, fv, t0, ts, tl)
        sa = sae * ie * tau / r_value
        df = pd.DataFrame({
            "T_s": np.round(periods, 4),
            "Sae_elastico_g": np.round(sae, 5),
            "Sa_diseno_g": np.round(sa, 5),
        })
        return df, {"T0": t0, "Ts": ts, "TL": tl}

    # ======================================================
    # MAIN FLOW
    # ======================================================
    def calculate(self):
        try:
            self.inputs = self._read_inputs()
            self._validate_inputs(self.inputs)

            soil_class = self.inputs["soil_class"]
            pga_s0 = self.inputs["PGA_S0"]
            structure_type = self.inputs["structure_type"]
            structure_code = STRUCTURE_TYPES[structure_type]["code"]

            ie, ie_just = self.get_importance_factor(structure_type, self.inputs.get("Ie_manual"))
            r_value, cd_value, deriva_max, system_just = self.get_structural_system_values(
                self.inputs["system_name"],
                self.inputs.get("R_manual"),
                self.inputs.get("Cd_manual"),
                self.inputs.get("Deriva_manual"),
            )
            tau, topo_info = self.calculate_topographic_factor(
                self.inputs["tau_mode"],
                self.inputs.get("tau_manual"),
                self.inputs.get("H"),
                self.inputs.get("I"),
                self.inputs.get("i"),
            )

            fa = self.inputs["Fa"]
            fv = self.inputs["Fv"]
            fa_method = self.inputs["Fa_method"]
            fv_method = self.inputs["Fv_method"]
            fa_mode_label = self.inputs["FaFv_mode_label"]
            fa_interpolation = self.inputs["Fa_interpolation"]
            fv_interpolation = self.inputs["Fv_interpolation"]

            cds_fa, cds_fv, cds_final, fas0, fvs0 = self.calculate_cds(pga_s0, fa, fv, structure_code)
            self.spectrum_df, periods = self.calculate_spectrum(
                pga_s0, fa, fv, ie, tau, r_value, self.inputs["Tmin"], self.inputs["Tmax"], self.inputs["dT"]
            )

            sae_0 = self._sae_at_period(0.0, pga_s0, fa, fv, periods["T0"], periods["Ts"], periods["TL"])
            sa_0 = sae_0 * ie * tau / r_value

            self.results = {
                "project_name": self.inputs["project_name"],
                "location": self.inputs["location"],
                "responsible": self.inputs["responsible"],
                "PGA_S0": pga_s0,
                "soil_class": soil_class,
                "structure_type": structure_type,
                "system_name": self.inputs["system_name"],
                "Fa": fa,
                "Fv": fv,
                "FaS0": fas0,
                "FvS0": fvs0,
                "FaFv_mode_label": fa_mode_label,
                "Fa_method": fa_method,
                "Fv_method": fv_method,
                "Fa_interpolation": fa_interpolation,
                "Fv_interpolation": fv_interpolation,
                "Fa_justification": self.inputs["Fa_justification"],
                "Fv_justification": self.inputs["Fv_justification"],
                "Ie": ie,
                "Ie_justification": ie_just,
                "Ie_method": "Automatico segun tipo de estructura" if STRUCTURE_TYPES[structure_type]["ie"] is not None else "Manual",
                "tau": tau,
                "tau_justification": topo_info["justification"],
                "tau_method": (
                    "Sin efecto topografico" if self.inputs["tau_mode"] == "Sin efecto topografico: tau = 1.00"
                    else "Manual" if self.inputs["tau_mode"] == "Ingresar tau manualmente"
                    else "Calculado por pendiente"
                ),
                "R": r_value,
                "Cd": cd_value,
                "deriva_max": deriva_max,
                "system_justification": system_just,
                "system_method": "Automatico segun sistema estructural" if self.inputs["system_name"] != "Manual" else "Manual",
                "T0": periods["T0"],
                "Ts": periods["Ts"],
                "TL": periods["TL"],
                "CDS_fa": cds_fa,
                "CDS_fv": cds_fv,
                "CDS_final": cds_final,
                "Tmin": self.inputs["Tmin"],
                "Tmax": self.inputs["Tmax"],
                "dT": self.inputs["dT"],
                "Sae_0": sae_0,
                "Sa_0": sa_0,
                "Sae_max": float(self.spectrum_df["Sae_elastico_g"].max()),
                "Sa_max": float(self.spectrum_df["Sa_diseno_g"].max()),
                "topo_a": topo_info["a"],
                "topo_b": topo_info["b"],
                "topo_c": topo_info["c"],
            }

            self._render_results()
            self._fill_spectrum_table()
            self.create_spectrum_plot(self.spectrum_df, self.results["T0"], self.results["Ts"], self.results["TL"])
            self.tabs.setCurrentWidget(self.tab_results)

        except Exception as exc:
            QMessageBox.warning(self, "Error de calculo", str(exc))

    def _read_inputs(self):
        values = {
            "project_name": self.project_name.text().strip(),
            "location": self.location.text().strip(),
            "responsible": self.responsible.text().strip(),
            "PGA_S0": self._float(self.pga_input),
            "soil_class": self._soil_class(),
            "structure_type": self.structure_combo.currentText(),
            "system_name": self.system_combo.currentText(),
            "tau_mode": self.tau_mode.currentText(),
            "Tmin": self._float(self.tmin_input),
            "Tmax": self._float(self.tmax_input),
            "dT": self._float(self.dt_input),
        }

        ffv_method = self.ffv_method_combo.currentText()
        soil_class = values["soil_class"]
        if ffv_method == "Automatico segun NBDS 2023" and soil_class != "S5":
            values["Fa"] = self.get_fa(values["PGA_S0"], soil_class)
            values["Fv"] = self.get_fv(values["PGA_S0"], soil_class)
            values["Fa_method"] = "Automatico NBDS 2023 con interpolacion lineal"
            values["Fv_method"] = "Automatico NBDS 2023 con interpolacion lineal"
            values["FaFv_mode_label"] = "Automatico NBDS 2023 con interpolacion lineal"
            values["Fa_interpolation"] = self.get_fa_detail(values["PGA_S0"], soil_class)
            values["Fv_interpolation"] = self.get_fv_detail(values["PGA_S0"], soil_class)
            values["Fa_justification"] = "Se obtuvo automaticamente de la tabla Fa de la NBDS 2023 para el suelo seleccionado y PGA_S0 ingresado, aplicando interpolacion lineal cuando corresponde."
            values["Fv_justification"] = "Se obtuvo automaticamente de la tabla Fv de la NBDS 2023 para el suelo seleccionado y PGA_S0 ingresado, aplicando interpolacion lineal cuando corresponde."
        elif ffv_method == "Automatico segun NBDS 2023" and soil_class == "S5":
            values["Fa"] = self._float(self.fa_manual)
            values["Fv"] = self._float(self.fv_manual)
            values["Fa_method"] = "Manual por suelo S5"
            values["Fv_method"] = "Manual por suelo S5"
            values["FaFv_mode_label"] = "Manual por suelo S5"
            values["Fa_interpolation"] = None
            values["Fv_interpolation"] = None
            values["Fa_justification"] = "Valor ingresado manualmente porque el suelo S5 requiere estudio tecnico especial."
            values["Fv_justification"] = "Valor ingresado manualmente porque el suelo S5 requiere estudio tecnico especial."
        else:
            values["Fa"] = self._float(self.fa_manual)
            values["Fv"] = self._float(self.fv_manual)
            values["Fa_method"] = "Manual / avanzado"
            values["Fv_method"] = "Manual / avanzado"
            values["FaFv_mode_label"] = "Manual / avanzado"
            values["Fa_interpolation"] = None
            values["Fv_interpolation"] = None
            values["Fa_justification"] = "Valor ingresado manualmente por el usuario. Debe verificarse con estudio tecnico o criterio profesional."
            values["Fv_justification"] = "Valor ingresado manualmente por el usuario. Debe verificarse con estudio tecnico o criterio profesional."

        if STRUCTURE_TYPES[values["structure_type"]]["ie"] is None:
            values["Ie_manual"] = self._float(self.ie_manual)
        if values["system_name"] == "Manual":
            values["R_manual"] = self._float(self.r_manual)
            values["Cd_manual"] = self._float(self.cd_manual)
            values["Deriva_manual"] = self._float(self.deriva_manual)
        if values["tau_mode"] == "Ingresar tau manualmente":
            values["tau_manual"] = self._float(self.tau_manual)
        if values["tau_mode"] == "Calcular tau por pendiente":
            values["H"] = self._float(self.H_input)
            values["I"] = self._float(self.I_input)
            values["i"] = self._float(self.i_input)

        return values

    def _validate_inputs(self, values):
        if values["PGA_S0"] <= 0:
            raise ValueError("PGA_S0 debe ser mayor que 0.")
        if values["PGA_S0"] > 1:
            raise ValueError("PGA_S0 debe ingresarse como fraccion de g. Ejemplo: 0.16, no 16.")
        if values["Fa"] <= 0:
            raise ValueError("Fa debe ser mayor que 0.")
        if values["Fv"] <= 0:
            raise ValueError("Fv debe ser mayor que 0.")
        if values["soil_class"] == "S5" and (values["Fa"] <= 0 or values["Fv"] <= 0):
            raise ValueError("Si el suelo es S5 debes ingresar Fa y Fv manuales validos.")
        if values["Tmax"] <= values["Tmin"]:
            raise ValueError("Tmax debe ser mayor que Tmin.")
        if values["dT"] <= 0:
            raise ValueError("dT debe ser mayor que 0.")
        if STRUCTURE_TYPES[values["structure_type"]]["ie"] is None and values["Ie_manual"] <= 0:
            raise ValueError("Ie manual debe ser mayor que 0.")
        if values["system_name"] == "Manual":
            if values["R_manual"] <= 0 or values["Cd_manual"] <= 0 or values["Deriva_manual"] <= 0:
                raise ValueError("R, Cd y deriva maxima manuales deben ser mayores que 0.")
        if values["tau_mode"] == "Ingresar tau manualmente" and values["tau_manual"] <= 0:
            raise ValueError("tau manual debe ser mayor que 0.")

    # ======================================================
    # PDF MAPA
    # ======================================================
    def _load_default_map_pdf(self):
        if self.pdf_document is None:
            self.map_status_label.setText(
                f"PDF sugerido: {DEFAULT_MAP_PDF}. Usa 'Abrir PDF completo' si deseas revisarlo fuera del visor."
            )
            return

        if DEFAULT_MAP_PDF.exists():
            self._load_pdf_document(DEFAULT_MAP_PDF)
        else:
            self.map_status_label.setText(
                f"No se encontro el PDF del proyecto en {DEFAULT_MAP_PDF}. "
                "Puedes volver a colocarlo en la carpeta assets/normativa."
            )
            self._update_pdf_ui_state()

    def _load_pdf_document(self, pdf_path: Path):
        if self.pdf_document is None:
            return
        self.pdf_document.load(str(pdf_path))
        self.current_pdf_path = pdf_path
        self.current_pdf_page = 0
        self.current_zoom_factor = 1.0
        if self.pdf_view is not None:
            self.pdf_view.setZoomFactor(self.current_zoom_factor)
            self._jump_to_pdf_page(0)
        self.map_status_label.setText(
            f"PDF cargado: {pdf_path.name}. Usa zoom y cambio de pagina para buscar el mapa de amenaza."
        )
        self._update_pdf_ui_state()

    def _update_pdf_ui_state(self):
        if self.pdf_document is None or self.pdf_view is None or self.pdf_document.pageCount() <= 0:
            self.map_page_label.setText("Pagina: -")
            self.map_zoom_label.setText(f"Zoom: {self.current_zoom_factor * 100:.0f}%")
            return
        self.map_page_label.setText(f"Pagina: {self.current_pdf_page + 1}/{self.pdf_document.pageCount()}")
        self.map_zoom_label.setText(f"Zoom: {self.current_zoom_factor * 100:.0f}%")

    def _change_pdf_page(self, delta):
        if self.pdf_document is None or self.pdf_view is None or self.pdf_document.pageCount() <= 0:
            return
        new_page = max(0, min(self.pdf_document.pageCount() - 1, self.current_pdf_page + delta))
        self._jump_to_pdf_page(new_page)
        self._update_pdf_ui_state()

    def _change_pdf_zoom(self, factor):
        if self.pdf_view is None:
            return
        self.current_zoom_factor = max(0.25, min(5.0, self.current_zoom_factor * factor))
        self.pdf_view.setZoomMode(QPdfView.ZoomMode.Custom)
        self.pdf_view.setZoomFactor(self.current_zoom_factor)
        self._update_pdf_ui_state()

    def _fit_pdf_width(self):
        if self.pdf_view is None:
            return
        self.pdf_view.setZoomMode(QPdfView.ZoomMode.FitToWidth)
        self.current_zoom_factor = 1.0
        self._update_pdf_ui_state()

    def _ask_pdf_page(self):
        if self.pdf_document is None or self.pdf_document.pageCount() <= 0 or self.pdf_view is None:
            return
        page_number, accepted = QInputDialog.getInt(
            self,
            "Ir a pagina",
            "Numero de pagina:",
            self.current_pdf_page + 1,
            1,
            self.pdf_document.pageCount(),
            1,
        )
        if accepted:
            self._jump_to_pdf_page(page_number - 1)
            self._update_pdf_ui_state()

    def _jump_to_pdf_page(self, page_number):
        if self.pdf_view is None:
            return
        self.current_pdf_page = page_number
        navigator = getattr(self.pdf_view, "pageNavigator", None)
        if callable(navigator):
            try:
                navigator().jump(page_number, QPointF(0, 0), self.current_zoom_factor)
                return
            except Exception:
                pass

    def _open_map_pdf_external(self):
        if DEFAULT_MAP_PDF.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(DEFAULT_MAP_PDF)))
        else:
            QMessageBox.information(
                self,
                "PDF no encontrado",
                f"No se encontro el PDF del proyecto en:\n{DEFAULT_MAP_PDF}",
            )

    # ======================================================
    # RENDER
    # ======================================================
    def _find_value_at_period(self, target_period):
        idx = (self.spectrum_df["T_s"] - target_period).abs().idxmin()
        return float(self.spectrum_df.loc[idx, "Sae_elastico_g"]), float(self.spectrum_df.loc[idx, "Sa_diseno_g"])

    def _control_rows(self):
        sae_1, sa_1 = self._find_value_at_period(1.0)
        sae_2, sa_2 = self._find_value_at_period(2.0)
        return [
            ["T0", f"{self.results['T0']:.5f} s"],
            ["Ts", f"{self.results['Ts']:.5f} s"],
            ["TL", f"{self.results['TL']:.5f} s"],
            ["Sae(0)", f"{self.results['Sae_0']:.5f} g"],
            ["Sa(0)", f"{self.results['Sa_0']:.5f} g"],
            ["Sae maximo", f"{self.results['Sae_max']:.5f} g"],
            ["Sa diseno maximo", f"{self.results['Sa_max']:.5f} g"],
            ["Sae en T = 1 s", f"{sae_1:.5f} g"],
            ["Sa en T = 1 s", f"{sa_1:.5f} g"],
            ["Sae en T = 2 s", f"{sae_2:.5f} g"],
            ["Sa en T = 2 s", f"{sa_2:.5f} g"],
        ]

    def _concept_rows(self):
        return [
            ["PGA_S0", f"{self.results['PGA_S0']:.5f}", "Representa la aceleracion maxima probable del suelo del sitio, expresada como fraccion de g.", "Valor ingresado por el usuario segun el mapa de amenaza sismica de la NBDS 2023.", "Entrada del usuario"],
            ["Tipo de suelo", self.results["soil_class"], "Clasifica el terreno de fundacion y controla la amplificacion sismica local.", "Se selecciono directamente en la interfaz.", "Seleccion del usuario"],
            ["Fa", f"{self.results['Fa']:.5f}", "Coeficiente de sitio para periodos cortos. Modifica la zona de aceleracion constante del espectro.", self.results["Fa_justification"], self.results["Fa_method"]],
            ["Fv", f"{self.results['Fv']:.5f}", "Coeficiente de sitio para periodos largos. Modifica la rama descendente del espectro.", self.results["Fv_justification"], self.results["Fv_method"]],
            ["Ie", f"{self.results['Ie']:.5f}", "Factor de importancia. Incrementa la demanda sismica en estructuras cuyo funcionamiento o seguridad es mas critico.", self.results["Ie_justification"], self.results["Ie_method"]],
            ["tau", f"{self.results['tau']:.5f}", "Factor topografico. Amplifica la demanda sismica cuando la edificacion se ubica cerca de crestas o pendientes significativas.", self.results["tau_justification"], self.results["tau_method"]],
            ["R", f"{self.results['R']:.5f}", "Factor de reduccion de respuesta. Representa la capacidad de disipacion de energia y ductilidad del sistema estructural.", self.results["system_justification"], self.results["system_method"]],
            ["Cd", f"{self.results['Cd']:.5f}", "Factor de amplificacion de desplazamientos. Se usa para estimar desplazamientos sismicos inelasticos.", self.results["system_justification"], self.results["system_method"]],
            ["Deriva maxima", f"{self.results['deriva_max']:.5f}", "Deriva maxima admisible del sistema estructural seleccionado.", self.results["system_justification"], self.results["system_method"]],
            ["T0", f"{self.results['T0']:.5f}", "Periodo inicial del espectro, limite entre la rama ascendente y la meseta.", "Se calculo con T0 = 0.15 * Fv / Fa.", "Formula NBDS 2023"],
            ["Ts", f"{self.results['Ts']:.5f}", "Periodo de transicion entre la meseta de aceleracion constante y la rama de velocidad constante.", "Se calculo con Ts = 0.50 * Fv / Fa.", "Formula NBDS 2023"],
            ["TL", f"{self.results['TL']:.5f}", "Periodo largo de transicion hacia la rama controlada por desplazamiento.", "Se calculo con TL = 4.00 * Fv / Fa.", "Formula NBDS 2023"],
            ["Sae", "Variable con T", "Aceleracion espectral elastica para cada periodo T.", "Se calculo por tramos segun la NBDS 2023.", "Formula NBDS 2023"],
            ["Sa", "Variable con T", "Aceleracion espectral de diseno obtenida reduciendo Sae por R y considerando Ie y tau.", "Se calculo con Sa = Sae * Ie * tau / R.", "Formula NBDS 2023"],
            ["CDS", self.results["CDS_final"], "Categoria de diseno sismico que resume el nivel de exigencia sismica segun amenaza, suelo e importancia.", "Se tomo la categoria mas desfavorable entre FaS0 y FvS0 y luego se aplicaron las reglas especiales por PGA_S0.", "Clasificacion NBDS 2023"],
        ]

    def _render_results(self):
        summary_lines = [
            "REPORTE TECNICO DE ESPECTRO SISMICO - NBDS 2023",
            "",
            "1. DATOS INGRESADOS",
            f"- PGA_S0 = {self.results['PGA_S0']:.5f} g",
            f"- Tipo de suelo = {self.results['soil_class']}",
            f"- Metodo Fa/Fv = {self.results['FaFv_mode_label']}",
            f"- Tipo de estructura = {self.results['structure_type']}",
            f"- Sistema estructural = {self.results['system_name']}",
            f"- Condicion topografica = {self.inputs['tau_mode']}",
            f"- Tmin = {self.results['Tmin']:.4f} s",
            f"- Tmax = {self.results['Tmax']:.4f} s",
            f"- dT = {self.results['dT']:.4f} s",
            "",
            "2. COEFICIENTES CALCULADOS",
            f"- Fa = {self.results['Fa']:.5f}",
            f"- Fv = {self.results['Fv']:.5f}",
            f"- Fa * PGA_S0 = {self.results['FaS0']:.5f}",
            f"- Fv * PGA_S0 = {self.results['FvS0']:.5f}",
            f"- Ie = {self.results['Ie']:.5f}",
            f"- tau = {self.results['tau']:.5f}",
            f"- R = {self.results['R']:.5f}",
            f"- Cd = {self.results['Cd']:.5f}",
            f"- deriva maxima = {self.results['deriva_max']:.5f}",
            f"- T0 = {self.results['T0']:.5f} s",
            f"- Ts = {self.results['Ts']:.5f} s",
            f"- TL = {self.results['TL']:.5f} s",
            f"- CDS por Fa = {self.results['CDS_fa']}",
            f"- CDS por Fv = {self.results['CDS_fv']}",
            f"- CDS final = {self.results['CDS_final']}",
        ]
        if self.results["topo_a"] is not None:
            summary_lines.extend([
                "",
                "3. PARAMETROS TOPOGRAFICOS AUXILIARES",
                f"- a = {self.results['topo_a']:.5f} m",
                f"- b = {self.results['topo_b']:.5f} m",
                f"- c = {self.results['topo_c']:.5f} m",
            ])
        self.summary_text.setPlainText("\n".join(summary_lines))

        control_rows = self._control_rows()
        self.control_table.setRowCount(len(control_rows))
        for row_idx, row in enumerate(control_rows):
            for col_idx, value in enumerate(row):
                item = QTableWidgetItem(str(value))
                item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                self.control_table.setItem(row_idx, col_idx, item)
        self.control_table.resizeColumnsToContents()

        concept_rows = self._concept_rows()
        self.concept_table.setRowCount(len(concept_rows))
        for row_idx, row in enumerate(concept_rows):
            for col_idx, value in enumerate(row):
                item = QTableWidgetItem(str(value))
                item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                self.concept_table.setItem(row_idx, col_idx, item)
        self.concept_table.resizeColumnsToContents()

    def _fill_spectrum_table(self):
        self.spectrum_table.setRowCount(len(self.spectrum_df))
        self.spectrum_table.setColumnCount(len(self.spectrum_df.columns))
        self.spectrum_table.setHorizontalHeaderLabels(list(self.spectrum_df.columns))
        for row_idx, (_, row) in enumerate(self.spectrum_df.iterrows()):
            for col_idx, value in enumerate(row):
                item = QTableWidgetItem(str(value))
                item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                self.spectrum_table.setItem(row_idx, col_idx, item)
        self.spectrum_table.resizeColumnsToContents()

    def create_spectrum_plot(self, df, t0, ts, tl):
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        ax.plot(df["T_s"], df["Sae_elastico_g"], label="Espectro elastico Sae", linewidth=2)
        ax.plot(df["T_s"], df["Sa_diseno_g"], label="Espectro de diseno Sa", linewidth=2)
        ax.axvline(t0, linestyle="--", label=f"T0 = {t0:.3f} s")
        ax.axvline(ts, linestyle="--", label=f"Ts = {ts:.3f} s")
        ax.axvline(tl, linestyle="--", label=f"TL = {tl:.3f} s")
        ax.set_xlabel("Periodo T (s)")
        ax.set_ylabel("Aceleracion espectral (g)")
        ax.set_title("Espectros sismicos NBDS 2023")
        ax.grid(True)
        ax.legend()
        self.fig.tight_layout()
        self.canvas.draw()

    # ======================================================
    # EXPORTS
    # ======================================================
    def _export_table(self, fmt):
        if self.spectrum_df.empty:
            QMessageBox.information(self, "Aviso", "Primero debes calcular el espectro.")
            return

        filters = {
            "csv": "Archivo CSV (*.csv)",
            "xlsx": "Archivo Excel (*.xlsx)",
            "txt": "Archivo TXT (*.txt)",
        }
        path, _ = QFileDialog.getSaveFileName(self, "Guardar tabla del espectro", "", filters[fmt])
        if not path:
            return

        if fmt == "csv":
            self.spectrum_df.to_csv(path, index=False)
        elif fmt == "txt":
            self.spectrum_df.to_csv(path, index=False, sep="\t")
        else:
            with pd.ExcelWriter(path, engine="openpyxl") as writer:
                self.spectrum_df.to_excel(writer, index=False, sheet_name="Espectro")

        QMessageBox.information(self, "Exportacion", "Archivo guardado correctamente.")

    def _export_plot_png(self):
        if self.spectrum_df.empty:
            QMessageBox.information(self, "Aviso", "Primero debes calcular el espectro.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Guardar grafica", "", "Imagen PNG (*.png)")
        if not path:
            return
        self.fig.savefig(path, format="png", dpi=180, bbox_inches="tight")
        QMessageBox.information(self, "Exportacion", "Grafica guardada correctamente.")

    def _export_pdf(self):
        if self.spectrum_df.empty:
            QMessageBox.information(self, "Aviso", "Primero debes calcular el espectro.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Guardar reporte PDF", "", "Archivo PDF (*.pdf)")
        if not path:
            return
        self._create_pdf_report(path)
        QMessageBox.information(self, "Exportacion", "Reporte PDF guardado correctamente.")

    # ======================================================
    # PDF
    # ======================================================
    def _table_from_dict_matrix(self, x_values, table_dict):
        headers = ["Suelo"] + [f"{value:.3f}" for value in x_values]
        rows = [headers]
        for soil_key in ["S0", "S1", "S2", "S3", "S4"]:
            rows.append([soil_key] + [f"{value:.3f}" for value in table_dict[soil_key]])
        return rows

    def _interpolation_rows(self, parameter_name, detail, method_label):
        rows = [["Parametro", "Dato", "Valor"]]
        if detail is None:
            rows.append([parameter_name, "Metodo", method_label])
            rows.append([parameter_name, "Observacion", "No aplica interpolacion automatica para este caso."])
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

    def _representative_spectrum_rows(self):
        periods = [0.0, self.results["T0"], self.results["Ts"], self.results["TL"], self.results["Tmax"]]
        unique = []
        for period in periods:
            if not any(abs(period - item) < 1e-9 for item in unique):
                unique.append(period)
        arr = np.array(unique, dtype=float)
        sae = self.calculate_sae(arr, self.results["PGA_S0"], self.results["Fa"], self.results["Fv"], self.results["T0"], self.results["Ts"], self.results["TL"])
        sa = sae * self.results["Ie"] * self.results["tau"] / self.results["R"]
        rows = [["T (s)", "Sae_elastico_g", "Sa_diseno_g"]]
        for t_val, sae_val, sa_val in zip(arr, sae, sa):
            rows.append([f"{t_val:.4f}", f"{sae_val:.5f}", f"{sa_val:.5f}"])
        return rows

    def _pdf_table(self, rows, col_widths, font_size=8, header=True):
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

    def _create_pdf_report(self, path):
        doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=1.5 * cm, rightMargin=1.5 * cm, topMargin=1.2 * cm, bottomMargin=1.2 * cm)
        styles = getSampleStyleSheet()
        story = []

        story.append(Paragraph("Reporte tecnico de espectro sismico - NBDS 2023", styles["Title"]))
        story.append(Spacer(1, 0.3 * cm))

        project_rows = [
            ["Nombre del proyecto", self.results["project_name"] or "-"],
            ["Ubicacion", self.results["location"] or "-"],
            ["Fecha de generacion", datetime.now().strftime("%Y-%m-%d %H:%M")],
            ["Responsable", self.results["responsible"] or "-"],
        ]
        story.append(self._pdf_table(project_rows, [5 * cm, 11 * cm], header=False))
        story.append(Spacer(1, 0.3 * cm))

        input_rows = [
            ["Parametro", "Valor"],
            ["PGA_S0", f"{self.results['PGA_S0']:.5f} g"],
            ["Tipo de suelo", self.results["soil_class"]],
            ["Metodo Fa/Fv", self.results["FaFv_mode_label"]],
            ["Fa", f"{self.results['Fa']:.5f}"],
            ["Fv", f"{self.results['Fv']:.5f}"],
            ["Tipo de estructura", self.results["structure_type"]],
            ["Ie", f"{self.results['Ie']:.5f}"],
            ["Sistema estructural", self.results["system_name"]],
            ["R", f"{self.results['R']:.5f}"],
            ["Cd", f"{self.results['Cd']:.5f}"],
            ["Deriva maxima", f"{self.results['deriva_max']:.5f}"],
            ["tau", f"{self.results['tau']:.5f}"],
            ["Tmin", f"{self.results['Tmin']:.4f} s"],
            ["Tmax", f"{self.results['Tmax']:.4f} s"],
            ["dT", f"{self.results['dT']:.4f} s"],
        ]
        story.append(Paragraph("Datos de entrada", styles["Heading2"]))
        story.append(self._pdf_table(input_rows, [7 * cm, 9 * cm]))
        story.append(Spacer(1, 0.3 * cm))

        story.append(Paragraph("Base normativa para coeficientes de sitio", styles["Heading2"]))
        story.append(Paragraph("Tabla Fa de la NBDS 2023", styles["Heading3"]))
        story.append(self._pdf_table(self._table_from_dict_matrix(FA_X, FA_TABLE), [1.6 * cm] + [2.35 * cm] * 6, font_size=7))
        story.append(Spacer(1, 0.2 * cm))
        story.append(Paragraph("Tabla Fv de la NBDS 2023", styles["Heading3"]))
        story.append(self._pdf_table(self._table_from_dict_matrix(FV_X, FV_TABLE), [1.6 * cm] + [2.35 * cm] * 6, font_size=7))
        story.append(Spacer(1, 0.3 * cm))

        story.append(Paragraph("Detalle tecnico de obtencion de Fa y Fv", styles["Heading2"]))
        story.append(Paragraph("Fa", styles["Heading3"]))
        story.append(self._pdf_table(self._interpolation_rows("Fa", self.results["Fa_interpolation"], self.results["Fa_method"]), [2.0 * cm, 3.4 * cm, 10.1 * cm], font_size=7))
        story.append(Spacer(1, 0.2 * cm))
        story.append(Paragraph("Fv", styles["Heading3"]))
        story.append(self._pdf_table(self._interpolation_rows("Fv", self.results["Fv_interpolation"], self.results["Fv_method"]), [2.0 * cm, 3.4 * cm, 10.1 * cm], font_size=7))
        story.append(Spacer(1, 0.3 * cm))

        result_rows = [
            ["Parametro", "Valor"],
            ["T0", f"{self.results['T0']:.5f} s"],
            ["Ts", f"{self.results['Ts']:.5f} s"],
            ["TL", f"{self.results['TL']:.5f} s"],
            ["CDS final", self.results["CDS_final"]],
            ["Sae maximo", f"{self.results['Sae_max']:.5f} g"],
            ["Sa diseno maximo", f"{self.results['Sa_max']:.5f} g"],
        ]
        story.append(Paragraph("Resultados principales", styles["Heading2"]))
        story.append(self._pdf_table(result_rows, [7 * cm, 9 * cm]))
        story.append(Spacer(1, 0.3 * cm))

        story.append(Paragraph("Tabla de control del espectro", styles["Heading2"]))
        story.append(self._pdf_table([["Parametro", "Valor"]] + self._control_rows(), [7 * cm, 9 * cm]))
        story.append(Spacer(1, 0.3 * cm))

        story.append(Paragraph("Desarrollo numerico de formulas", styles["Heading2"]))
        development_lines = [
            f"Fa * PGA_S0 = {self.results['Fa']:.5f} * {self.results['PGA_S0']:.5f} = {self.results['FaS0']:.5f}",
            f"Fv * PGA_S0 = {self.results['Fv']:.5f} * {self.results['PGA_S0']:.5f} = {self.results['FvS0']:.5f}",
            f"T0 = 0.15 * Fv / Fa = 0.15 * {self.results['Fv']:.5f} / {self.results['Fa']:.5f} = {self.results['T0']:.5f} s",
            f"Ts = 0.50 * Fv / Fa = 0.50 * {self.results['Fv']:.5f} / {self.results['Fa']:.5f} = {self.results['Ts']:.5f} s",
            f"TL = 4.00 * Fv / Fa = 4.00 * {self.results['Fv']:.5f} / {self.results['Fa']:.5f} = {self.results['TL']:.5f} s",
            f"Sae(0) = Fa * PGA_S0 = {self.results['Fa']:.5f} * {self.results['PGA_S0']:.5f} = {self.results['Sae_0']:.5f} g",
            f"Sa(0) = Sae(0) * Ie * tau / R = {self.results['Sae_0']:.5f} * {self.results['Ie']:.5f} * {self.results['tau']:.5f} / {self.results['R']:.5f} = {self.results['Sa_0']:.5f} g",
            f"Meseta elastica = 2.5 * Fa * PGA_S0 = 2.5 * {self.results['Fa']:.5f} * {self.results['PGA_S0']:.5f} = {self.results['Sae_max']:.5f} g",
            f"Meseta de diseno = meseta elastica * Ie * tau / R = {self.results['Sae_max']:.5f} * {self.results['Ie']:.5f} * {self.results['tau']:.5f} / {self.results['R']:.5f} = {self.results['Sa_max']:.5f} g",
        ]
        for line in development_lines:
            story.append(Paragraph(line, styles["BodyText"]))
        story.append(Spacer(1, 0.3 * cm))

        story.append(Paragraph("Concepto y justificacion de cada valor", styles["Heading2"]))
        concept_rows = [["Parametro", "Valor", "Concepto", "Justificacion", "Metodo"]] + self._concept_rows()
        story.append(self._pdf_table(concept_rows, [2.5 * cm, 2.0 * cm, 4.5 * cm, 4.6 * cm, 2.4 * cm], font_size=6))
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
            ["1", f"0 <= T < {self.results['T0']:.5f} s", "Sae = Fa * PGA_S0 * (1 + 1.5 * T / T0)", "Rama ascendente inicial; parte en Sae(0) = Fa * PGA_S0."],
            ["2", f"{self.results['T0']:.5f} <= T <= {self.results['Ts']:.5f} s", "Sae = 2.5 * Fa * PGA_S0", "Meseta de aceleracion espectral constante."],
            ["3", f"{self.results['Ts']:.5f} < T <= {self.results['TL']:.5f} s", "Sae = 1.25 * Fv * PGA_S0 / T", "Rama descendente controlada por velocidad."],
            ["4", f"T > {self.results['TL']:.5f} s", "Sae = 1.25 * Fv * PGA_S0 * TL / T^2", "Rama descendente controlada por desplazamiento."],
        ]
        story.append(self._pdf_table(tramo_rows, [1.1 * cm, 4.2 * cm, 5.2 * cm, 5.2 * cm], font_size=7))
        story.append(Spacer(1, 0.3 * cm))

        image_buffer = BytesIO()
        self.fig.savefig(image_buffer, format="png", dpi=180, bbox_inches="tight")
        image_buffer.seek(0)
        story.append(Paragraph("Grafica", styles["Heading2"]))
        story.append(Image(image_buffer, width=16 * cm, height=8.5 * cm))
        story.append(Spacer(1, 0.3 * cm))

        story.append(Paragraph("Tabla reducida del espectro", styles["Heading2"]))
        story.append(self._pdf_table(self._representative_spectrum_rows(), [4 * cm, 5 * cm, 5 * cm]))
        story.append(Paragraph("La tabla completa del espectro puede descargarse en CSV, Excel o TXT desde la pestana Tabla del espectro.", styles["BodyText"]))
        story.append(Spacer(1, 0.3 * cm))

        story.append(Paragraph("Advertencias", styles["Heading2"]))
        warnings = []
        if self.results["soil_class"] == "S5":
            warnings.append("Advertencia: el suelo S5 requiere analisis especial de respuesta de sitio.")
        if self.results["Fa_method"] != "Automatico NBDS 2023 con interpolacion lineal" or self.results["Fv_method"] != "Automatico NBDS 2023 con interpolacion lineal":
            warnings.append("Advertencia: Fa y Fv fueron ingresados manualmente y deben verificarse con estudio tecnico.")
        warnings.append("Este reporte es una herramienta de apoyo al calculo. El diseno final debe ser revisado y firmado por un profesional competente.")
        for warning in warnings:
            story.append(Paragraph(warning, styles["BodyText"]))

        doc.build(story)
