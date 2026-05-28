from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QListWidget

from ui.inicio_view import InicioView
from ui.columnas_view import ColumnasView
from ui.vigas_view import VigasView
from ui.zapatas_view import ZapatasView
from ui.sismo_view import SismoView
from ui.reporte_view import ReporteView


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Diseño Estructural ACI")
        self.resize(1000, 700)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout_principal = QHBoxLayout(central_widget)

        self.menu = QListWidget()
        self.menu.addItems([
            "Inicio",
            "Columnas",
            "Vigas",
            "Zapatas",
            "Sismo",
            "Viento"
        ])

        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)

        layout_principal.addWidget(self.menu, 1)
        layout_principal.addWidget(self.container, 4)

        self.menu.currentRowChanged.connect(self.cambiar_vista)
        self.menu.setCurrentRow(0)

    def cambiar_vista(self, index: int):
        while self.container_layout.count():
            item = self.container_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        if index == 0:
            view = InicioView()
        elif index == 1:
            view = ColumnasView()
        elif index == 2:
            view = VigasView()
        elif index == 3:
            view = ZapatasView()
        elif index == 4:
            view = SismoView()
        elif index == 5:
            view = ReporteView()
        else:
            view = InicioView()

        self.container_layout.addWidget(view)
