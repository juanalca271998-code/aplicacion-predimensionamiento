from __future__ import annotations

from datetime import datetime
from io import BytesIO
from pathlib import Path

import numpy as np
import pandas as pd
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QPixmap
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
    QPushButton,
    QScrollArea,
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

from data.storage import guardar_resultado

try:
    from PySide6.QtPdf import QPdfDocument
    from PySide6.QtPdfWidgets import QPdfView
    PDF_VIEW_AVAILABLE = True
except Exception:
    QPdfDocument = None
    QPdfView = None
    PDF_VIEW_AVAILABLE = False


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WIND_PDF = PROJECT_ROOT / "assets" / "normativa" / "NB-1225003-1.pdf"
DEFAULT_WIND_REFERENCE_IMAGE = PROJECT_ROOT / "assets" / "normativa" / "viento_tabla_velocidades_crop.jpg"
DEFAULT_WIND_REFERENCE_IMAGE_P19 = PROJECT_ROOT / "assets" / "normativa" / "viento_pagina_19_crop.jpg"

IMPORTANCE_FACTORS = {
    "Categoria IV - Esencial o critica": 1.15,
    "Categoria III - Alta ocupacion": 1.15,
    "Categoria II - Uso comun": 1.00,
    "Categoria I - Menor riesgo para la vida": 0.87,
    "Manual": None,
}

EXPOSURE_GUIDE = {
    "A": "Centros densamente urbanizados con edificios altos y numerosos obstaculos cercanos. Revisar con especial cuidado porque la pagina 19 de la norma solo se usa aqui como guia visual.",
    "B": "Areas urbanas, suburbanas o industriales con construcciones frecuentes y obstaculos regulares alrededor de la estructura.",
    "C": "Terreno abierto con obstaculos dispersos. Es comun en zonas periurbanas, campos abiertos y sectores con baja rugosidad superficial.",
    "D": "Costas, lagos grandes o terrenos muy expuestos al viento con poca o nula proteccion superficial.",
}

EXPOSURE_PARAMS = {
    "B": {"alpha": 7.0, "zg_m": 366.0, "zmin_m": 9.14, "descripcion": EXPOSURE_GUIDE["B"]},
    "C": {"alpha": 9.5, "zg_m": 274.0, "zmin_m": 4.57, "descripcion": EXPOSURE_GUIDE["C"]},
    "D": {"alpha": 11.5, "zg_m": 213.0, "zmin_m": 4.57, "descripcion": EXPOSURE_GUIDE["D"]},
}

ENCLOSURE_GCPI = {
    "Cerrada": 0.18,
    "Parcialmente cerrada": 0.55,
    "Abierta": 0.00,
    "Manual": None,
}

CP_PRESETS = {
    "Edificio rectangular basico": {
        "windward": 0.80,
        "leeward": -0.50,
        "side": -0.70,
        "roof_up": -0.90,
        "roof_down": 0.30,
    },
    "Nave baja / cubierta liviana": {
        "windward": 0.80,
        "leeward": -0.60,
        "side": -0.70,
        "roof_up": -1.00,
        "roof_down": 0.20,
    },
    "Manual": {
        "windward": None,
        "leeward": None,
        "side": None,
        "roof_up": None,
        "roof_down": None,
    },
}


class ReporteView(QWidget):
    def __init__(self):
        super().__init__()

        self.wind_df = pd.DataFrame()
        self.results: dict[str, float | str] = {}
        self.fig = Figure(figsize=(8.6, 5.1))
        self.canvas = FigureCanvas(self.fig)
        self.guide_fig = Figure(figsize=(7.2, 4.2))
        self.guide_canvas = FigureCanvas(self.guide_fig)
        self.wind_pdf_document = QPdfDocument(self) if PDF_VIEW_AVAILABLE else None

        layout = QVBoxLayout(self)
        title = QLabel("MODULO VIENTO - ANALISIS PRELIMINAR SEGUN NB 1225003")
        title.setStyleSheet("font-size: 16px; font-weight: bold; padding: 4px;")
        layout.addWidget(title)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self.tab_inputs = QWidget()
        self.tab_guide = QWidget()
        self.tab_results = QWidget()
        self.tab_plot = QWidget()
        self.tab_pdf = QWidget()
        self.tabs.addTab(self.tab_inputs, "Datos de entrada")
        self.tabs.addTab(self.tab_guide, "Guia y norma")
        self.tabs.addTab(self.tab_results, "Resultados")
        self.tabs.addTab(self.tab_plot, "Grafica de viento")
        self.tabs.addTab(self.tab_pdf, "Reporte PDF")

        self._build_inputs_tab()
        self._build_guide_tab()
        self._build_results_tab()
        self._build_plot_tab()
        self._build_pdf_tab()
        self._update_visibility()

    # ======================================================
    # UI
    # ======================================================
    def _build_inputs_tab(self):
        outer = QVBoxLayout(self.tab_inputs)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        outer.addWidget(scroll)

        container = QWidget()
        scroll.setWidget(container)
        layout = QVBoxLayout(container)

        project_group = QGroupBox("Datos del proyecto")
        form = QFormLayout()
        self.project_name = QLineEdit()
        self.location = QLineEdit()
        self.responsible = QLineEdit()
        form.addRow("Nombre del proyecto", self.project_name)
        form.addRow("Ubicacion", self.location)
        form.addRow("Responsable", self.responsible)
        project_group.setLayout(form)
        layout.addWidget(project_group)

        wind_group = QGroupBox("Datos basicos de viento")
        form = QFormLayout()
        self.norm_label = QLabel(
            "Modulo preliminar de viento inspirado en el flujo de analisis de la NB 1225003. "
            "Usa velocidad basica, exposicion, topografia, direccion y coeficientes de presion."
        )
        self.norm_label.setWordWrap(True)
        self.norm_label.setStyleSheet("color: #2f4f4f;")
        self.wind_speed = QLineEdit("40")
        self.importance_combo = QComboBox()
        self.importance_combo.addItems(list(IMPORTANCE_FACTORS.keys()))
        self.importance_combo.currentTextChanged.connect(self._update_visibility)
        self.importance_manual = QLineEdit("1.00")
        self.exposure_combo = QComboBox()
        self.exposure_combo.addItems(list(EXPOSURE_PARAMS.keys()))
        self.exposure_help = QLabel(
            "La pagina 19 de la NB 1225003 muestra las categorias A, B, C y D. "
            "En este calculo preliminar se usan directamente B, C y D, que son las categorias ya parametrizadas en el modelo."
        )
        self.exposure_help.setWordWrap(True)
        self.exposure_help.setStyleSheet("color: #2f4f4f;")
        self.topographic_factor = QLineEdit("1.00")
        self.directionality_factor = QLineEdit("0.85")
        self.gust_factor = QLineEdit("0.85")
        self.enclosure_combo = QComboBox()
        self.enclosure_combo.addItems(list(ENCLOSURE_GCPI.keys()))
        self.enclosure_combo.currentTextChanged.connect(self._update_visibility)
        self.gcpi_manual = QLineEdit("0.18")
        form.addRow("", self.norm_label)
        form.addRow("Velocidad basica V (m/s)", self.wind_speed)
        form.addRow("Categoria / importancia", self.importance_combo)
        form.addRow("Factor de importancia I", self.importance_manual)
        form.addRow("Categoria de exposicion", self.exposure_combo)
        form.addRow("", self.exposure_help)
        form.addRow("Factor topografico Kzt", self.topographic_factor)
        form.addRow("Factor direccional Kd", self.directionality_factor)
        form.addRow("Factor de rafaga G", self.gust_factor)
        form.addRow("Condicion de cerramiento", self.enclosure_combo)
        form.addRow("GCpi", self.gcpi_manual)
        wind_group.setLayout(form)
        layout.addWidget(wind_group)

        geom_group = QGroupBox("Geometria del edificio")
        form = QFormLayout()
        self.width_b = QLineEdit("18")
        self.length_l = QLineEdit("24")
        self.height_h = QLineEdit("12")
        self.roof_slope = QLineEdit("10")
        self.z_min = QLineEdit("0")
        self.z_max = QLineEdit("12")
        self.dz = QLineEdit("1")
        form.addRow("Ancho B (m)", self.width_b)
        form.addRow("Largo L (m)", self.length_l)
        form.addRow("Altura media h (m)", self.height_h)
        form.addRow("Pendiente de cubierta (%)", self.roof_slope)
        form.addRow("Altura inicial z min (m)", self.z_min)
        form.addRow("Altura final z max (m)", self.z_max)
        form.addRow("Paso dz (m)", self.dz)
        self.height_help = QLabel(
            "h es la altura media del edificio sobre el terreno. En cubierta plana suele coincidir con la altura total. "
            "En cubierta inclinada, como ayuda preliminar, puedes usar el promedio entre alero y cumbrera. "
            "z min y z max definen el rango vertical donde se evaluan Kz, qz y las presiones."
        )
        self.height_help.setWordWrap(True)
        self.height_help.setStyleSheet("color: #2f4f4f;")
        form.addRow("", self.height_help)
        geom_group.setLayout(form)
        layout.addWidget(geom_group)

        cp_group = QGroupBox("Coeficientes de presion")
        cp_layout = QGridLayout()
        self.cp_preset = QComboBox()
        self.cp_preset.addItems(list(CP_PRESETS.keys()))
        self.cp_preset.currentTextChanged.connect(self._load_cp_preset)
        self.cp_windward = QLineEdit("0.80")
        self.cp_leeward = QLineEdit("-0.50")
        self.cp_side = QLineEdit("-0.70")
        self.cp_roof_up = QLineEdit("-0.90")
        self.cp_roof_down = QLineEdit("0.30")
        cp_layout.addWidget(QLabel("Perfil de coeficientes"), 0, 0)
        cp_layout.addWidget(self.cp_preset, 0, 1)
        cp_layout.addWidget(QLabel("Cp barlovento"), 1, 0)
        cp_layout.addWidget(self.cp_windward, 1, 1)
        cp_layout.addWidget(QLabel("Cp sotavento"), 2, 0)
        cp_layout.addWidget(self.cp_leeward, 2, 1)
        cp_layout.addWidget(QLabel("Cp lateral"), 3, 0)
        cp_layout.addWidget(self.cp_side, 3, 1)
        cp_layout.addWidget(QLabel("Cp cubierta succion"), 4, 0)
        cp_layout.addWidget(self.cp_roof_up, 4, 1)
        cp_layout.addWidget(QLabel("Cp cubierta presion"), 5, 0)
        cp_layout.addWidget(self.cp_roof_down, 5, 1)
        cp_group.setLayout(cp_layout)
        layout.addWidget(cp_group)

        btn_row = QHBoxLayout()
        self.calculate_button = QPushButton("Calcular viento")
        self.calculate_button.clicked.connect(self.calculate)
        self.clear_button = QPushButton("Limpiar")
        self.clear_button.clicked.connect(self._clear)
        btn_row.addWidget(self.calculate_button)
        btn_row.addWidget(self.clear_button)
        layout.addLayout(btn_row)
        layout.addStretch()

    def _build_results_tab(self):
        layout = QVBoxLayout(self.tab_results)
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        layout.addWidget(self.summary_text)

    def _build_guide_tab(self):
        outer = QVBoxLayout(self.tab_guide)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        outer.addWidget(scroll)
        container = QWidget()
        scroll.setWidget(container)
        layout = QVBoxLayout(container)

        intro = QTextEdit()
        intro.setReadOnly(True)
        intro.setPlainText(
            "GUIA RAPIDA PARA INTERPRETAR LOS DATOS DE VIENTO\n\n"
            "1. V es la velocidad basica del viento del sitio.\n"
            "2. h es la altura media del edificio respecto al terreno.\n"
            "3. z es la altura a la que se evalua Kz y qz; por eso el programa arma una tabla desde z min hasta z max.\n"
            "4. Si solo quieres revisar el edificio completo, normalmente conviene que z max llegue al menos hasta h.\n"
            "5. B y L son dimensiones en planta del edificio.\n"
            "6. I es el factor de importancia. En la pagina 19 de la norma se ve que Categoria I = 0.87, Categoria II = 1.00 y Categorias III y IV = 1.15.\n"
            "7. La exposicion depende del entorno que rodea a la estructura. La pagina 19 introduce A, B, C y D; este calculo preliminar usa directamente B, C y D.\n"
            "8. GCpi depende de si la envolvente es cerrada, parcialmente cerrada o abierta.\n"
            "9. Los Cp de muros y cubierta pueden elegirse por tipologia o ingresarse manualmente.\n\n"
            "Lectura practica:\n"
            "- qz cambia con la altura z.\n"
            "- qh es la presion dinamica evaluada a la altura media h del edificio.\n"
            "- Las presiones netas combinan efecto externo (Cp) e interno (GCpi)."
        )
        layout.addWidget(intro)

        fig_group = QGroupBox("Esquema visual")
        fig_layout = QVBoxLayout()
        fig_layout.addWidget(self.guide_canvas)
        fig_group.setLayout(fig_layout)
        layout.addWidget(fig_group)

        table_group = QGroupBox("Tablas de ayuda para elegir datos")
        table_layout = QVBoxLayout()
        self.guide_tables_text = QTextEdit()
        self.guide_tables_text.setReadOnly(True)
        self.guide_tables_text.setPlainText(
            "EXPOSICION\n"
            "- A: centros densamente urbanizados con edificios altos y numerosos obstaculos. Se muestra como referencia normativa de la pagina 19.\n"
            "- B: areas urbanas, suburbanas o industriales con obstaculos frecuentes.\n"
            "- C: terreno abierto con obstaculos dispersos.\n"
            "- D: costa, lago abierto o terreno muy expuesto.\n\n"
            "IMPORTANCIA\n"
            "- Categoria IV: I = 1.15.\n"
            "- Categoria III: I = 1.15.\n"
            "- Categoria II: uso comun.\n"
            "- Categoria I: I = 0.87.\n\n"
            "CERRAMIENTO\n"
            "- Cerrada: envolvente relativamente sellada.\n"
            "- Parcialmente cerrada: tiene aberturas significativas.\n"
            "- Abierta: flujo libre de viento a traves de la estructura."
        )
        table_layout.addWidget(self.guide_tables_text)
        table_group.setLayout(table_layout)
        layout.addWidget(table_group)

        ref_group = QGroupBox("Referencia normativa")
        ref_layout = QVBoxLayout()
        self.wind_ref_image_label = QLabel()
        self.wind_ref_image_label.setAlignment(Qt.AlignCenter)
        self.wind_ref_image_label.setWordWrap(True)
        self.wind_ref_image_label_2 = QLabel()
        self.wind_ref_image_label_2.setAlignment(Qt.AlignCenter)
        self.wind_ref_image_label_2.setWordWrap(True)
        if DEFAULT_WIND_REFERENCE_IMAGE.exists():
            pixmap = QPixmap(str(DEFAULT_WIND_REFERENCE_IMAGE))
            self.wind_ref_image_label.setPixmap(pixmap.scaledToWidth(760, Qt.SmoothTransformation))
            ref_layout.addWidget(QLabel("Recorte especifico de la tabla de velocidades basicas del viento"))
            ref_layout.addWidget(self.wind_ref_image_label)
        if DEFAULT_WIND_REFERENCE_IMAGE_P19.exists():
            pixmap2 = QPixmap(str(DEFAULT_WIND_REFERENCE_IMAGE_P19))
            self.wind_ref_image_label_2.setPixmap(pixmap2.scaledToWidth(760, Qt.SmoothTransformation))
            ref_layout.addWidget(QLabel("Recorte especifico de la pagina 19: factor de importancia I y comienzo de las categorias de exposicion"))
            ref_layout.addWidget(self.wind_ref_image_label_2)
        if PDF_VIEW_AVAILABLE:
            self.wind_pdf_status = QLabel("Mapa y norma de viento integrados en el proyecto.")
            self.wind_pdf_status.setStyleSheet("color: #2f4f4f;")
            ref_layout.addWidget(self.wind_pdf_status)
            self.wind_pdf_view = QPdfView()
            self.wind_pdf_view.setDocument(self.wind_pdf_document)
            self.wind_pdf_view.setMinimumHeight(520)
            try:
                self.wind_pdf_view.setZoomMode(QPdfView.ZoomMode.FitToWidth)
            except Exception:
                pass
            ref_layout.addWidget(self.wind_pdf_view)
            self._load_wind_pdf()
        else:
            note = QLabel("El visor integrado de PDF no esta disponible en esta instalacion. Puedes abrir la norma con el boton inferior.")
            note.setWordWrap(True)
            ref_layout.addWidget(note)
        ref_buttons = QHBoxLayout()
        self.open_norm_btn_guide = QPushButton("Abrir norma PDF")
        self.open_norm_btn_guide.clicked.connect(self._open_norm_pdf)
        ref_buttons.addWidget(self.open_norm_btn_guide)
        ref_group.setLayout(ref_layout)
        ref_layout.addLayout(ref_buttons)
        layout.addWidget(ref_group)

        self._draw_wind_guide()

    def _build_table_tab(self):
        layout = QVBoxLayout(self.tab_table)
        self.table_widget = QTableWidget()
        layout.addWidget(self.table_widget)
        btn_row = QHBoxLayout()
        self.export_csv_btn = QPushButton("Exportar CSV")
        self.export_csv_btn.clicked.connect(lambda: self._export_table("csv"))
        self.export_xlsx_btn = QPushButton("Exportar Excel")
        self.export_xlsx_btn.clicked.connect(lambda: self._export_table("xlsx"))
        self.export_txt_btn = QPushButton("Exportar TXT")
        self.export_txt_btn.clicked.connect(lambda: self._export_table("txt"))
        btn_row.addWidget(self.export_csv_btn)
        btn_row.addWidget(self.export_xlsx_btn)
        btn_row.addWidget(self.export_txt_btn)
        layout.addLayout(btn_row)

    def _build_plot_tab(self):
        layout = QVBoxLayout(self.tab_plot)
        self.plot_help = QLabel(
            "La grafica muestra un esquema del edificio con las presiones netas principales sobre muros y cubierta, "
            "para que la lectura sea mas directa y visual."
        )
        self.plot_help.setWordWrap(True)
        self.plot_help.setStyleSheet("color: #2f4f4f;")
        layout.addWidget(self.plot_help)
        layout.addWidget(self.canvas)
        self.export_plot_btn = QPushButton("Guardar grafica PNG")
        self.export_plot_btn.clicked.connect(self._export_plot)
        layout.addWidget(self.export_plot_btn)

    def _build_pdf_tab(self):
        layout = QVBoxLayout(self.tab_pdf)
        self.pdf_info = QTextEdit()
        self.pdf_info.setReadOnly(True)
        self.pdf_info.setPlainText(
            "El reporte PDF de viento incluira:\n"
            "- Datos del proyecto y del edificio\n"
            "- Factores de viento usados\n"
            "- Resumen tecnico y formulas empleadas\n"
            "- Grafica de cargas de viento sobre el edificio y la cubierta\n\n"
            "Nota: la norma local de viento proporcionada esta en PDF escaneado. "
            "Este modulo deja una base profesional de analisis preliminar y debe contrastarse "
            "con las clausulas exactas del proyecto definitivo."
        )
        layout.addWidget(self.pdf_info)

        btn_row = QHBoxLayout()
        self.open_norm_btn = QPushButton("Abrir norma PDF")
        self.open_norm_btn.clicked.connect(self._open_norm_pdf)
        self.export_pdf_btn = QPushButton("Generar reporte PDF")
        self.export_pdf_btn.clicked.connect(self._export_pdf)
        btn_row.addWidget(self.open_norm_btn)
        btn_row.addWidget(self.export_pdf_btn)
        layout.addLayout(btn_row)

    # ======================================================
    # HELPERS
    # ======================================================
    def _update_visibility(self):
        self.importance_manual.setEnabled(self.importance_combo.currentText() == "Manual")
        self.gcpi_manual.setEnabled(self.enclosure_combo.currentText() == "Manual")
        if self.importance_combo.currentText() != "Manual":
            self.importance_manual.setText(f"{IMPORTANCE_FACTORS[self.importance_combo.currentText()]:.2f}")
        if self.enclosure_combo.currentText() != "Manual":
            self.gcpi_manual.setText(f"{ENCLOSURE_GCPI[self.enclosure_combo.currentText()]:.2f}")

    def _load_cp_preset(self):
        preset = CP_PRESETS[self.cp_preset.currentText()]
        if preset["windward"] is not None:
            self.cp_windward.setText(f"{preset['windward']:.2f}")
            self.cp_leeward.setText(f"{preset['leeward']:.2f}")
            self.cp_side.setText(f"{preset['side']:.2f}")
            self.cp_roof_up.setText(f"{preset['roof_up']:.2f}")
            self.cp_roof_down.setText(f"{preset['roof_down']:.2f}")

    def _load_wind_pdf(self):
        if PDF_VIEW_AVAILABLE and self.wind_pdf_document and DEFAULT_WIND_PDF.exists():
            self.wind_pdf_document.load(str(DEFAULT_WIND_PDF))
            if hasattr(self, "wind_pdf_status"):
                self.wind_pdf_status.setText(
                    "La norma de viento se cargo desde la carpeta del proyecto. "
                    "Usa este visor para consultar el mapa de velocidades y las tablas."
                )
        elif hasattr(self, "wind_pdf_status"):
            self.wind_pdf_status.setText(
                "No se encontro el PDF de la norma dentro del proyecto. Puedes abrirlo manualmente si lo vuelves a copiar."
            )

    def _draw_wind_guide(self):
        self.guide_fig.clear()
        ax = self.guide_fig.add_subplot(111)
        ax.set_title("Significado geometrico de B, L, h y z")

        # Edificio esquematico
        x0, y0 = 0.18, 0.12
        width, height = 0.34, 0.58
        roof_peak = 0.78
        ax.plot([x0, x0 + width, x0 + width, x0, x0], [y0, y0, y0 + height, y0 + height, y0], color="black", linewidth=2)
        ax.plot([x0, x0 + width / 2.0, x0 + width], [y0 + height, roof_peak, y0 + height], color="firebrick", linewidth=2)
        ax.fill([x0, x0 + width, x0 + width, x0], [y0, y0, y0 + height, y0 + height], color="#ddeaf6", alpha=0.8)

        # Viento
        for yy in [0.25, 0.40, 0.55]:
            ax.annotate("", xy=(x0 - 0.02, yy), xytext=(0.02, yy), arrowprops=dict(arrowstyle="->", color="#1f77b4", linewidth=2))
        ax.text(0.01, 0.62, "Direccion del viento", color="#1f77b4", ha="left")

        # h and z
        ax.annotate("", xy=(x0 + width + 0.08, y0), xytext=(x0 + width + 0.08, y0 + (height + roof_peak - (y0 + height)) / 2.0 + height), arrowprops=dict(arrowstyle="<->", color="black"))
        ax.text(x0 + width + 0.1, 0.47, "h = altura media\nsobre terreno", va="center")
        ax.annotate("", xy=(x0 + width + 0.18, y0), xytext=(x0 + width + 0.18, 0.46), arrowprops=dict(arrowstyle="<->", color="dimgray"))
        ax.text(x0 + width + 0.2, 0.32, "z = altura de\n evaluacion", va="center", color="dimgray")

        # B and L notes
        ax.annotate("", xy=(x0, y0 - 0.05), xytext=(x0 + width, y0 - 0.05), arrowprops=dict(arrowstyle="<->", color="black"))
        ax.text(x0 + width / 2.0, y0 - 0.09, "B = ancho en planta", ha="center")
        ax.text(0.64, 0.63, "L = largo en planta\n(perpendicular al corte)", va="center")

        ax.text(0.64, 0.18, "Para cubierta plana:\nh suele ser la altura total.\n\nPara cubierta inclinada:\ncomo ayuda preliminar, usa\nel promedio entre alero y cumbrera.", va="bottom")
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")
        self.guide_fig.tight_layout()
        self.guide_canvas.draw()

    def _read_inputs(self):
        data = {
            "project_name": self.project_name.text().strip(),
            "location": self.location.text().strip(),
            "responsible": self.responsible.text().strip(),
            "V": float(self.wind_speed.text()),
            "importance_label": self.importance_combo.currentText(),
            "I": float(self.importance_manual.text()),
            "exposure": self.exposure_combo.currentText(),
            "Kzt": float(self.topographic_factor.text()),
            "Kd": float(self.directionality_factor.text()),
            "G": float(self.gust_factor.text()),
            "enclosure": self.enclosure_combo.currentText(),
            "GCpi": float(self.gcpi_manual.text()),
            "B": float(self.width_b.text()),
            "L": float(self.length_l.text()),
            "h": float(self.height_h.text()),
            "roof_slope": float(self.roof_slope.text()),
            "zmin": float(self.z_min.text()),
            "zmax": float(self.z_max.text()),
            "dz": float(self.dz.text()),
            "Cp_w": float(self.cp_windward.text()),
            "Cp_l": float(self.cp_leeward.text()),
            "Cp_s": float(self.cp_side.text()),
            "Cp_ru": float(self.cp_roof_up.text()),
            "Cp_rd": float(self.cp_roof_down.text()),
        }
        self._validate_inputs(data)
        return data

    def _validate_inputs(self, d):
        if d["V"] <= 0:
            raise ValueError("La velocidad basica V debe ser mayor que cero.")
        if d["I"] <= 0 or d["Kzt"] <= 0 or d["Kd"] <= 0 or d["G"] <= 0:
            raise ValueError("Los factores I, Kzt, Kd y G deben ser mayores que cero.")
        if min(d["B"], d["L"], d["h"]) <= 0:
            raise ValueError("Las dimensiones del edificio deben ser mayores que cero.")
        if d["zmax"] <= d["zmin"]:
            raise ValueError("z max debe ser mayor que z min.")
        if d["dz"] <= 0:
            raise ValueError("El paso dz debe ser mayor que cero.")

    def _kz_at_height(self, z_m: float, exposure: str) -> float:
        params = EXPOSURE_PARAMS[exposure]
        z_eval = max(z_m, params["zmin_m"])
        kz = 2.01 * (z_eval / params["zg_m"]) ** (2.0 / params["alpha"])
        return max(kz, 0.01)

    def _velocity_pressure(self, kz: float, d: dict[str, float | str]) -> float:
        return 0.613 * kz * float(d["Kzt"]) * float(d["Kd"]) * (float(d["V"]) ** 2) * float(d["I"]) / 1000.0

    def _calculate_dataframe(self, d):
        z = np.arange(d["zmin"], d["zmax"] + d["dz"], d["dz"])
        z = np.unique(np.append(z, d["h"]))
        z.sort()

        kz = np.array([self._kz_at_height(float(item), d["exposure"]) for item in z])
        qz = np.array([self._velocity_pressure(float(item), d) for item in kz])
        kh = self._kz_at_height(d["h"], d["exposure"])
        qh = self._velocity_pressure(kh, d)
        gcpi_abs = abs(d["GCpi"])

        def envelope(cp_value: float):
            external = qz * float(d["G"]) * cp_value
            p_max = external + qh * gcpi_abs
            p_min = external - qh * gcpi_abs
            return p_max, p_min

        bw_max, bw_min = envelope(d["Cp_w"])
        lw_max, lw_min = envelope(d["Cp_l"])
        sw_max, sw_min = envelope(d["Cp_s"])
        roof_up_max, roof_up_min = envelope(d["Cp_ru"])
        roof_dn_max, roof_dn_min = envelope(d["Cp_rd"])

        df = pd.DataFrame(
            {
                "z_m": z,
                "Kz": kz,
                "qz_kPa": qz,
                "barlovento_max_kPa": bw_max,
                "barlovento_min_kPa": bw_min,
                "sotavento_max_kPa": lw_max,
                "sotavento_min_kPa": lw_min,
                "lateral_max_kPa": sw_max,
                "lateral_min_kPa": sw_min,
                "cubierta_succion_max_kPa": roof_up_max,
                "cubierta_succion_min_kPa": roof_up_min,
                "cubierta_presion_max_kPa": roof_dn_max,
                "cubierta_presion_min_kPa": roof_dn_min,
            }
        )
        return df, kh, qh

    def _concept_table(self, d, kh, qh):
        importance_note = (
            f"Seleccionado como {d['importance_label']} segun la referencia visual de la pagina 19 de la norma"
            if d["importance_label"] != "Manual"
            else "Valor ingresado manualmente por el usuario"
        )
        return pd.DataFrame(
            [
                ["V", f"{d['V']:.2f} m/s", "Velocidad basica del viento", "Dato base del sitio o criterio de proyecto"],
                ["I", f"{d['I']:.3f}", "Factor de importancia", importance_note],
                ["Exposicion", str(d["exposure"]), "Categoria de rugosidad / entorno", EXPOSURE_PARAMS[d["exposure"]]["descripcion"]],
                ["Kzt", f"{d['Kzt']:.3f}", "Factor topografico", "Ajusta el efecto de lomas, crestas o relieve"],
                ["Kd", f"{d['Kd']:.3f}", "Factor direccional", "Reduce la probabilidad de maxima accion simultanea"],
                ["G", f"{d['G']:.3f}", "Factor de rafaga", "Representa amplificacion dinamica simplificada"],
                ["GCpi", f"{d['GCpi']:.3f}", "Coeficiente interno", f"Condicion de cerramiento: {d['enclosure']}"],
                ["Kz(h)", f"{kh:.4f}", "Factor de exposicion a la altura media", "Calculado con la ley de exposicion adoptada"],
                ["qh", f"{qh:.4f} kPa", "Presion dinamica a la altura del edificio", "qh = 0.613 Kz Kzt Kd V^2 I / 1000"],
            ],
            columns=["Parametro", "Valor", "Concepto", "Justificacion"],
        )

    # ======================================================
    # FLOW
    # ======================================================
    def calculate(self):
        try:
            data = self._read_inputs()
            df, kh, qh = self._calculate_dataframe(data)
            self.wind_df = df
            self.results = {
                **data,
                "kh": kh,
                "qh": qh,
                "qz_max": float(df["qz_kPa"].max()),
                "barlovento_max": float(df["barlovento_max_kPa"].max()),
                "sotavento_min": float(df["sotavento_min_kPa"].min()),
                "lateral_min": float(df["lateral_min_kPa"].min()),
                "roof_up_min": float(df["cubierta_succion_min_kPa"].min()),
                "roof_dn_max": float(df["cubierta_presion_max_kPa"].max()),
            }
            self._update_summary()
            self._update_plot()
            guardar_resultado("viento", {"resumen_texto": self.summary_text.toPlainText(), "tabla": df.to_dict(orient="records")})
            self.tabs.setCurrentWidget(self.tab_results)
        except Exception as e:
            QMessageBox.warning(self, "Error de datos", f"Revisa los valores ingresados.\n\n{e}")

    def _update_summary(self):
        d = self.results
        concept_df = self._concept_table(d, d["kh"], d["qh"])
        lines = [
            "=== ANALISIS PRELIMINAR DE VIENTO ===",
            "",
            f"Proyecto: {d.get('project_name') or 'No indicado'}",
            f"Ubicacion: {d.get('location') or 'No indicada'}",
            f"Norma base de referencia: NB 1225003",
            "",
            "Datos principales:",
            f"- Velocidad basica V = {d['V']:.2f} m/s",
            f"- Categoria / importancia = {d['importance_label']}",
            f"- Exposicion = {d['exposure']}",
            f"- I = {d['I']:.3f}",
            f"- Kzt = {d['Kzt']:.3f}",
            f"- Kd = {d['Kd']:.3f}",
            f"- G = {d['G']:.3f}",
            f"- GCpi = {d['GCpi']:.3f}",
            "",
            "Geometria:",
            f"- B = {d['B']:.2f} m",
            f"- L = {d['L']:.2f} m",
            f"- h = {d['h']:.2f} m",
            f"- Pendiente de cubierta = {d['roof_slope']:.2f} %",
            "",
            "Resultados clave:",
            f"- Kz(h) = {d['kh']:.4f}",
            f"- qh = {d['qh']:.4f} kPa",
            f"- qz maxima evaluada = {d['qz_max']:.4f} kPa",
            f"- Barlovento maximo = {d['barlovento_max']:.4f} kPa",
            f"- Sotavento minimo = {d['sotavento_min']:.4f} kPa",
            f"- Lateral minimo = {d['lateral_min']:.4f} kPa",
            f"- Cubierta succion minima = {d['roof_up_min']:.4f} kPa",
            f"- Cubierta presion maxima = {d['roof_dn_max']:.4f} kPa",
            "",
            "Conceptos y justificaciones:",
        ]
        for _, row in concept_df.iterrows():
            lines.append(f"- {row['Parametro']}: {row['Valor']} | {row['Concepto']} | {row['Justificacion']}")
        lines.extend(
            [
                "",
                "Advertencia tecnica:",
                "- Este modulo es una herramienta preliminar de viento. Debe cotejarse con los apartados exactos del proyecto definitivo segun la NB 1225003 y el criterio profesional correspondiente.",
                "- La pagina 19 de la norma se usa aqui como apoyo visual para elegir I y orientar la exposicion. Si el caso real es dudoso, conviene revisar directamente la norma completa.",
            ]
        )
        self.summary_text.setPlainText("\n".join(lines))

    def _update_plot(self):
        self.fig.clear()
        if self.wind_df.empty:
            self.canvas.draw()
            return

        B = float(self.results["B"])
        L = float(self.results["L"])
        h = float(self.results["h"])
        roof_slope = float(self.results["roof_slope"])
        roof_rise = max(0.10 * h, min(0.35 * h, h * roof_slope / 100.0))
        barlovento = float(self.results["barlovento_max"])
        sotavento = float(self.results["sotavento_min"])
        lateral = float(self.results["lateral_min"])
        roof_up = float(self.results["roof_up_min"])
        roof_dn = float(self.results["roof_dn_max"])

        gs = self.fig.add_gridspec(1, 2, width_ratios=[2.2, 1.0], wspace=0.22)
        ax_alzado = self.fig.add_subplot(gs[0, 0])
        ax_planta = self.fig.add_subplot(gs[0, 1])

        x0 = 0.0
        x1 = B
        y0 = 0.0
        y1 = h
        xr = B / 2.0
        yr = h + roof_rise

        ax_alzado.fill([x0, x1, x1, x0], [y0, y0, y1, y1], color="#e8f1fa", alpha=0.92)
        ax_alzado.plot([x0, x1, x1, x0, x0], [y0, y0, y1, y1, y0], color="black", linewidth=2)
        ax_alzado.plot([x0, xr, x1], [y1, yr, y1], color="firebrick", linewidth=2)

        for yy in np.linspace(0.18 * h, 0.82 * h, 4):
            ax_alzado.annotate(
                "",
                xy=(x0 + 0.08 * B, yy),
                xytext=(x0 - 0.28 * B, yy),
                arrowprops=dict(arrowstyle="->", color="#1f77b4", linewidth=2),
            )
        ax_alzado.text(x0 - 0.30 * B, 0.97 * h, "Direccion del viento", color="#1f77b4", ha="left", fontweight="bold")

        for yy in np.linspace(0.22 * h, 0.78 * h, 3):
            ax_alzado.annotate(
                "",
                xy=(x0 + 0.02 * B, yy),
                xytext=(x0 - 0.10 * B, yy),
                arrowprops=dict(arrowstyle="-|>", color="#d62728", linewidth=2),
            )
        ax_alzado.text(
            x0 - 0.18 * B,
            0.50 * h,
            f"Barlovento\n{barlovento:.3f} kPa",
            color="#d62728",
            ha="center",
            va="center",
            bbox=dict(boxstyle="round,pad=0.28", facecolor="white", edgecolor="#d62728", alpha=0.95),
        )

        for yy in np.linspace(0.22 * h, 0.78 * h, 3):
            ax_alzado.annotate(
                "",
                xy=(x1 + 0.12 * B, yy),
                xytext=(x1 - 0.02 * B, yy),
                arrowprops=dict(arrowstyle="-|>", color="#2ca02c", linewidth=2),
            )
        ax_alzado.text(
            x1 + 0.30 * B,
            0.46 * h,
            f"Sotavento\n{sotavento:.3f} kPa",
            color="#2ca02c",
            ha="center",
            va="center",
            bbox=dict(boxstyle="round,pad=0.28", facecolor="white", edgecolor="#2ca02c", alpha=0.95),
        )

        ax_alzado.annotate(
            "",
            xy=(xr - 0.14 * B, yr + 0.15 * h),
            xytext=(xr - 0.14 * B, yr + 0.02 * h),
            arrowprops=dict(arrowstyle="-|>", color="#9467bd", linewidth=2),
        )
        ax_alzado.text(
            x0 - 0.46 * B,
            yr + 0.30 * h,
            f"Cubierta succion\n{roof_up:.3f} kPa",
            color="#9467bd",
            ha="left",
            va="bottom",
            bbox=dict(boxstyle="round,pad=0.28", facecolor="white", edgecolor="#9467bd", alpha=0.95),
        )
        ax_alzado.annotate(
            "",
            xy=(xr + 0.18 * B, yr - 0.01 * h),
            xytext=(xr + 0.18 * B, yr + 0.12 * h),
            arrowprops=dict(arrowstyle="-|>", color="#ff7f0e", linewidth=2),
        )
        ax_alzado.text(
            x1 - 0.02 * B,
            yr + 0.24 * h,
            f"Cubierta presion\n{roof_dn:.3f} kPa",
            color="#ff7f0e",
            ha="left",
            va="bottom",
            bbox=dict(boxstyle="round,pad=0.28", facecolor="white", edgecolor="#ff7f0e", alpha=0.95),
        )

        ax_alzado.annotate("", xy=(x0, -0.08 * h), xytext=(x1, -0.08 * h), arrowprops=dict(arrowstyle="<->", color="black"))
        ax_alzado.text((x0 + x1) / 2.0, -0.13 * h, f"B = {B:.2f} m", ha="center")
        ax_alzado.annotate("", xy=(x1 + 0.08 * B, y0), xytext=(x1 + 0.08 * B, y1), arrowprops=dict(arrowstyle="<->", color="black"))
        ax_alzado.text(x1 + 0.11 * B, (y0 + y1) / 2.0, f"h = {h:.2f} m", rotation=90, va="center")
        ax_alzado.annotate("", xy=(x1 + 0.20 * B, y1), xytext=(x1 + 0.20 * B, yr), arrowprops=dict(arrowstyle="<->", color="firebrick"))
        ax_alzado.text(x1 + 0.23 * B, (y1 + yr) / 2.0, f"f = {roof_rise:.2f} m", rotation=90, va="center", color="firebrick")
        ax_alzado.annotate("", xy=(x0, y1 + 0.03 * h), xytext=(xr, yr + 0.03 * h), arrowprops=dict(arrowstyle="<->", color="firebrick"))
        ax_alzado.text(0.5 * (x0 + xr) - 0.03 * B, yr + 0.04 * h, f"Pendiente = {roof_slope:.1f} %", ha="center", color="firebrick")

        ax_alzado.text(
            x0 + 0.30 * B,
            yr + 0.24 * h,
            (
                f"qh = {self.results['qh']:.3f} kPa\n"
                f"Kz(h) = {self.results['kh']:.3f}\n"
                f"Exposicion = {self.results['exposure']}\n"
                f"Presion lateral = {lateral:.3f} kPa"
            ),
            bbox=dict(boxstyle="round,pad=0.38", facecolor="#f5f7fa", edgecolor="#8aa0b8"),
            ha="left",
            va="bottom",
        )

        ax_alzado.set_title("Alzado cargado")
        ax_alzado.set_xlim(-0.58 * B, 1.52 * B)
        ax_alzado.set_ylim(-0.22 * h, yr + 0.58 * h)
        ax_alzado.set_aspect("equal", adjustable="box")
        ax_alzado.axis("off")

        px0 = 0.0
        py0 = 0.0
        px1 = B
        py1 = L
        ax_planta.fill([px0, px1, px1, px0], [py0, py0, py1, py1], color="#f7f4ea", alpha=0.95)
        ax_planta.plot([px0, px1, px1, px0, px0], [py0, py0, py1, py1, py0], color="black", linewidth=1.8)

        ymid = 0.58 * L
        ax_planta.annotate("", xy=(0.10 * B, ymid), xytext=(-0.32 * B, ymid), arrowprops=dict(arrowstyle="->", color="#1f77b4", linewidth=2))
        ax_planta.text(-0.24 * B, ymid + 0.10 * L, "Viento", color="#1f77b4", ha="left", fontweight="bold")
        ax_planta.annotate("", xy=(0.04 * B, ymid), xytext=(-0.12 * B, ymid), arrowprops=dict(arrowstyle="-|>", color="#d62728", linewidth=1.8))
        ax_planta.annotate("", xy=(1.12 * B, ymid), xytext=(0.96 * B, ymid), arrowprops=dict(arrowstyle="-|>", color="#2ca02c", linewidth=1.8))
        ax_planta.annotate("", xy=(0.50 * B, 1.12 * L), xytext=(0.50 * B, 0.98 * L), arrowprops=dict(arrowstyle="-|>", color="#6f42c1", linewidth=1.8))
        ax_planta.annotate("", xy=(0.50 * B, -0.12 * L), xytext=(0.50 * B, 0.02 * L), arrowprops=dict(arrowstyle="-|>", color="#6f42c1", linewidth=1.8))

        ax_planta.text(
            0.50 * B,
            1.12 * L,
            f"Lateral\n{lateral:.3f} kPa",
            color="#6f42c1",
            ha="center",
            va="bottom",
            bbox=dict(boxstyle="round,pad=0.25", facecolor="white", edgecolor="#6f42c1", alpha=0.95),
        )
        ax_planta.text(
            -0.18 * B,
            ymid + 0.28 * L,
            f"Barlovento\n{barlovento:.3f} kPa",
            color="#d62728",
            ha="center",
            va="center",
            bbox=dict(boxstyle="round,pad=0.25", facecolor="white", edgecolor="#d62728", alpha=0.95),
        )
        ax_planta.text(
            1.34 * B,
            ymid + 0.28 * L,
            f"Sotavento\n{sotavento:.3f} kPa",
            color="#2ca02c",
            ha="center",
            va="center",
            bbox=dict(boxstyle="round,pad=0.25", facecolor="white", edgecolor="#2ca02c", alpha=0.95),
        )

        ax_planta.annotate("", xy=(px0, -0.08 * L), xytext=(px1, -0.08 * L), arrowprops=dict(arrowstyle="<->", color="black"))
        ax_planta.text(0.50 * B, -0.13 * L, f"B = {B:.2f} m", ha="center")
        ax_planta.annotate("", xy=(1.08 * B, py0), xytext=(1.08 * B, py1), arrowprops=dict(arrowstyle="<->", color="black"))
        ax_planta.text(1.12 * B, 0.50 * L, f"L = {L:.2f} m", rotation=90, va="center")

        ax_planta.set_title("Planta y composicion alrededor")
        ax_planta.set_xlim(-0.42 * B, 1.48 * B)
        ax_planta.set_ylim(-0.22 * L, 1.32 * L)
        ax_planta.set_aspect("equal", adjustable="box")
        ax_planta.axis("off")

        self.fig.suptitle("Cargas netas de viento sobre edificio y cubierta", fontsize=13, y=0.98)

        self.fig.tight_layout()
        self.canvas.draw()

    # ======================================================
    # EXPORTS
    # ======================================================
    def _export_table(self, fmt: str):
        if self.wind_df.empty:
            QMessageBox.information(self, "Aviso", "Primero debes calcular.")
            return
        filters = {
            "csv": "CSV (*.csv)",
            "xlsx": "Excel (*.xlsx)",
            "txt": "TXT (*.txt)",
        }
        path, _ = QFileDialog.getSaveFileName(self, "Guardar tabla de viento", "", filters[fmt])
        if not path:
            return
        if fmt == "csv":
            self.wind_df.to_csv(path, index=False)
        elif fmt == "xlsx":
            self.wind_df.to_excel(path, index=False)
        else:
            self.wind_df.to_csv(path, index=False, sep="\t")
        QMessageBox.information(self, "Exportacion", "Tabla guardada correctamente.")

    def _export_plot(self):
        if self.wind_df.empty:
            QMessageBox.information(self, "Aviso", "Primero debes calcular.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Guardar grafica", "", "Imagen PNG (*.png)")
        if not path:
            return
        self.fig.savefig(path, dpi=180, bbox_inches="tight")
        QMessageBox.information(self, "Exportacion", "Grafica guardada correctamente.")

    def _export_pdf(self):
        if self.wind_df.empty:
            QMessageBox.information(self, "Aviso", "Primero debes calcular.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Guardar reporte PDF", "", "Archivo PDF (*.pdf)")
        if not path:
            return
        self._build_pdf(path)
        QMessageBox.information(self, "Exportacion", "Reporte PDF guardado correctamente.")

    def _build_pdf(self, path: str):
        buffer = BytesIO()
        self.fig.savefig(buffer, format="png", dpi=180, bbox_inches="tight")
        buffer.seek(0)

        doc = SimpleDocTemplate(path, pagesize=A4, rightMargin=1.4 * cm, leftMargin=1.4 * cm, topMargin=1.4 * cm, bottomMargin=1.4 * cm)
        styles = getSampleStyleSheet()
        story = []

        story.append(Paragraph("Reporte tecnico de viento - NB 1225003", styles["Title"]))
        story.append(Spacer(1, 0.3 * cm))
        story.append(Paragraph(f"Fecha de generacion: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles["Normal"]))
        story.append(Paragraph(f"Proyecto: {self.results.get('project_name') or 'No indicado'}", styles["Normal"]))
        story.append(Paragraph(f"Ubicacion: {self.results.get('location') or 'No indicada'}", styles["Normal"]))
        story.append(Paragraph(f"Responsable: {self.results.get('responsible') or 'No indicado'}", styles["Normal"]))
        story.append(Spacer(1, 0.25 * cm))

        inputs_table = Table(
            [
                ["Parametro", "Valor"],
                ["V", f"{self.results['V']:.2f} m/s"],
                ["Categoria / importancia", self.results["importance_label"]],
                ["Exposicion", self.results["exposure"]],
                ["I", f"{self.results['I']:.3f}"],
                ["Kzt", f"{self.results['Kzt']:.3f}"],
                ["Kd", f"{self.results['Kd']:.3f}"],
                ["G", f"{self.results['G']:.3f}"],
                ["GCpi", f"{self.results['GCpi']:.3f}"],
                ["B", f"{self.results['B']:.2f} m"],
                ["L", f"{self.results['L']:.2f} m"],
                ["h", f"{self.results['h']:.2f} m"],
            ],
            colWidths=[6.0 * cm, 8.5 * cm],
        )
        inputs_table.setStyle(self._table_style())
        story.append(Paragraph("1. Datos de entrada", styles["Heading2"]))
        story.append(inputs_table)
        story.append(Spacer(1, 0.3 * cm))

        story.append(Paragraph("2. Formulas empleadas", styles["Heading2"]))
        for formula in [
            "Kz = 2.01 (z / zg)^(2 / alpha)",
            "qz = 0.613 Kz Kzt Kd V^2 I / 1000",
            "p_ext = qz G Cp",
            "p_neta,max = p_ext + qh |GCpi|",
            "p_neta,min = p_ext - qh |GCpi|",
        ]:
            story.append(Paragraph(formula, styles["Code"]))
        story.append(Spacer(1, 0.2 * cm))

        story.append(Paragraph("3. Resultados principales", styles["Heading2"]))
        result_table = Table(
            [
                ["Magnitud", "Valor"],
                ["Kz(h)", f"{self.results['kh']:.4f}"],
                ["qh", f"{self.results['qh']:.4f} kPa"],
                ["qz maxima", f"{self.results['qz_max']:.4f} kPa"],
                ["Barlovento max", f"{self.results['barlovento_max']:.4f} kPa"],
                ["Sotavento min", f"{self.results['sotavento_min']:.4f} kPa"],
                ["Lateral min", f"{self.results['lateral_min']:.4f} kPa"],
                ["Cubierta succion min", f"{self.results['roof_up_min']:.4f} kPa"],
                ["Cubierta presion max", f"{self.results['roof_dn_max']:.4f} kPa"],
            ],
            colWidths=[6.5 * cm, 8.0 * cm],
        )
        result_table.setStyle(self._table_style())
        story.append(result_table)
        story.append(Spacer(1, 0.3 * cm))

        story.append(Paragraph("4. Grafica", styles["Heading2"]))
        story.append(Image(buffer, width=16 * cm, height=9 * cm))
        story.append(Spacer(1, 0.3 * cm))

        reduced = self.wind_df.iloc[[0, max(0, len(self.wind_df) // 2), len(self.wind_df) - 1]][["z_m", "Kz", "qz_kPa", "barlovento_max_kPa", "sotavento_min_kPa"]]
        reduced_rows = [["z_m", "Kz", "qz_kPa", "barlovento_max_kPa", "sotavento_min_kPa"]]
        for _, row in reduced.iterrows():
            reduced_rows.append([f"{row[c]:.4f}" for c in reduced.columns])
        story.append(Paragraph("5. Tabla reducida de control", styles["Heading2"]))
        reduced_table = Table(reduced_rows, colWidths=[2.2 * cm] * 5)
        reduced_table.setStyle(self._table_style())
        story.append(reduced_table)
        story.append(Spacer(1, 0.3 * cm))

        story.append(Paragraph("6. Advertencia tecnica", styles["Heading2"]))
        story.append(
            Paragraph(
                "Este modulo es una herramienta de apoyo para analisis preliminar de viento. "
                "La norma local provista se encuentra escaneada, por lo que el modelo implementado "
                "debe contrastarse con los articulos y tablas exactas de la NB 1225003 en la etapa de diseno final.",
                styles["Normal"],
            )
        )

        doc.build(story)

    def _table_style(self):
        return TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d9e8f5")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.HexColor("#eef5fb")]),
            ]
        )

    def _open_norm_pdf(self):
        if DEFAULT_WIND_PDF.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(DEFAULT_WIND_PDF)))
            return
        QMessageBox.information(
            self,
            "Norma no encontrada",
            "No encontre la norma de viento dentro de la carpeta del proyecto. Si quieres, la integro tambien como recurso interno.",
        )

    def _clear(self):
        self.project_name.clear()
        self.location.clear()
        self.responsible.clear()
        self.wind_speed.setText("40")
        self.importance_combo.setCurrentIndex(0)
        self.exposure_combo.setCurrentIndex(0)
        self.topographic_factor.setText("1.00")
        self.directionality_factor.setText("0.85")
        self.gust_factor.setText("0.85")
        self.enclosure_combo.setCurrentIndex(0)
        self.width_b.setText("18")
        self.length_l.setText("24")
        self.height_h.setText("12")
        self.roof_slope.setText("10")
        self.z_min.setText("0")
        self.z_max.setText("12")
        self.dz.setText("1")
        self.cp_preset.setCurrentIndex(0)
        self._load_cp_preset()
        self._update_visibility()
        self.wind_df = pd.DataFrame()
        self.results = {}
        self.summary_text.clear()
        self.fig.clear()
        self.canvas.draw()
