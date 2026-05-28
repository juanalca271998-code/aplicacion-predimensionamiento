# AciBolAC Predimensionamiento Estructural

Aplicacion tecnica de predimensionamiento estructural creada por Ing. Juan Alex Callisaya Acho.

## Aplicacion principal

La app principal es:

`AciBolAC_Predimensionamiento_Estructural_ACERO_MOMENTO_2CAPAS_OK`

Archivos incluidos:

- `dist/AciBolAC_Predimensionamiento_Estructural_ACERO_MOMENTO_2CAPAS_OK.exe`
- `dist/AciBolAC_Predimensionamiento_Estructural_ACERO_MOMENTO_2CAPAS_OK.zip`
- `AciBolAC_EXE_BUILD/index.html`
- `AciBolAC_EXE_BUILD/check-script.js`
- `AciBolAC_EXE_BUILD/AciBolAC.cs`
- `AciBolAC_EXE_BUILD/AciBolAC.ico`

## Ejecutar en Windows

Abre el ejecutable:

```text
dist/AciBolAC_Predimensionamiento_Estructural_ACERO_MOMENTO_2CAPAS_OK.exe
```

Tambien puedes abrir directamente:

```text
AciBolAC_EXE_BUILD/index.html
```

## Modulos de la app AciBolAC

- Conversion de unidades
- Losas
- Vigas
- Columnas
- Plateas / radier
- Escaleras
- Acero para losas
- Acero por momento con opcion de 2 capas

## Proyecto Python adicional

El repositorio tambien conserva una version Python de calculo estructural con Streamlit y PySide6.

Ejecutar la app Streamlit:

```bash
pip install -r requirements.txt
streamlit run app.py
```

Ejecutar la app de escritorio Python:

```bash
pip install -r requirements.txt
python programa/main.py
```

## Nota tecnica

Los resultados son herramientas de apoyo al calculo. El diseno final debe verificarse con normativa vigente, combinaciones de carga, detallado de acero, deformaciones, cortante, punzonamiento, esbeltez y criterio profesional.

## Archivos grandes

El archivo local `programa/assets/normativa/NB-1225003-1.pdf` pesa mas de 100 MB y no se incluye en GitHub para evitar rechazo del push. Si lo necesitas, colocalo manualmente en esa ruta dentro del proyecto local.
