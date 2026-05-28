from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QGroupBox, QGridLayout,
    QComboBox, QPushButton, QMessageBox
)

from data.storage import guardar_configuracion, obtener_configuracion


class InicioView(QWidget):
    def __init__(self):
        super().__init__()

        self.config = obtener_configuracion()

        layout = QVBoxLayout(self)

        titulo = QLabel("INICIO DEL PROGRAMA")
        layout.addWidget(titulo)

        grupo = QGroupBox("Configuración general del proyecto")
        layout_grupo = QGridLayout()

        self.combo_fuerza = QComboBox()
        self.combo_fuerza.addItems(["kN", "tf", "kgf"])
        self.combo_fuerza.setCurrentText(self.config.get("unidad_fuerza", "kN"))

        self.combo_momento = QComboBox()
        self.combo_momento.addItems(["kN·m", "tf·m", "kgf·m"])
        self.combo_momento.setCurrentText(self.config.get("unidad_momento", "kN·m"))

        self.combo_longitud = QComboBox()
        self.combo_longitud.addItems(["mm", "cm", "m"])
        self.combo_longitud.setCurrentText(self.config.get("unidad_longitud", "mm"))

        self.combo_recubrimiento = QComboBox()
        self.combo_recubrimiento.addItems(["mm", "cm"])
        self.combo_recubrimiento.setCurrentText(self.config.get("unidad_recubrimiento", "mm"))

        self.combo_diametro = QComboBox()
        self.combo_diametro.addItems(["mm", "cm"])
        self.combo_diametro.setCurrentText(self.config.get("unidad_diametro_barra", "mm"))

        self.combo_area = QComboBox()
        self.combo_area.addItems(["mm²", "cm²"])
        self.combo_area.setCurrentText(self.config.get("unidad_area_acero", "mm²"))

        layout_grupo.addWidget(QLabel("Unidad de fuerza:"), 0, 0)
        layout_grupo.addWidget(self.combo_fuerza, 0, 1)

        layout_grupo.addWidget(QLabel("Unidad de momento:"), 1, 0)
        layout_grupo.addWidget(self.combo_momento, 1, 1)

        layout_grupo.addWidget(QLabel("Unidad geométrica de la sección:"), 2, 0)
        layout_grupo.addWidget(self.combo_longitud, 2, 1)

        layout_grupo.addWidget(QLabel("Unidad de recubrimiento:"), 3, 0)
        layout_grupo.addWidget(self.combo_recubrimiento, 3, 1)

        layout_grupo.addWidget(QLabel("Unidad de diámetros de barra:"), 4, 0)
        layout_grupo.addWidget(self.combo_diametro, 4, 1)

        layout_grupo.addWidget(QLabel("Unidad mostrada para área de acero:"), 5, 0)
        layout_grupo.addWidget(self.combo_area, 5, 1)

        nota = QLabel(
            "Notas:\n"
            "- Guarda aquí las unidades antes de entrar a Columnas.\n"
            "- Luego entra de nuevo a Columnas para ver las etiquetas actualizadas.\n"
            "- El programa convierte internamente las unidades a mm, kN y kN·m."
        )
        layout_grupo.addWidget(nota, 6, 0, 1, 2)

        grupo.setLayout(layout_grupo)
        layout.addWidget(grupo)

        self.btn_guardar = QPushButton("Guardar configuración")
        self.btn_guardar.clicked.connect(self.guardar)
        layout.addWidget(self.btn_guardar)

    def guardar(self):
        guardar_configuracion("unidad_fuerza", self.combo_fuerza.currentText())
        guardar_configuracion("unidad_momento", self.combo_momento.currentText())
        guardar_configuracion("unidad_longitud", self.combo_longitud.currentText())
        guardar_configuracion("unidad_recubrimiento", self.combo_recubrimiento.currentText())
        guardar_configuracion("unidad_diametro_barra", self.combo_diametro.currentText())
        guardar_configuracion("unidad_area_acero", self.combo_area.currentText())

        QMessageBox.information(
            self,
            "Configuración",
            "Configuración guardada.\nAhora entra nuevamente al módulo Columnas para ver las unidades actualizadas."
        )