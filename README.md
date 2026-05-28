# Aplicacion de calculo de hormigon

Aplicacion tecnica para calculo y predimensionamiento estructural de hormigon armado.

Incluye:

- Espectro sismico NBDS 2023 en Streamlit
- Modulos de vigas, columnas, zapatas, sismo, viento y reportes en PySide6
- Reportes PDF y exportacion de tablas

## Ejecutar la app Streamlit

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Ejecutar la app de escritorio

```bash
pip install -r requirements.txt
python programa/main.py
```

## Nota tecnica

Los resultados son herramientas de apoyo al calculo. El diseno final debe verificarse con normativa vigente, combinaciones de carga, detallado de acero, deformaciones, cortante, punzonamiento, esbeltez y criterio profesional.

## Archivos grandes

El archivo local `programa/assets/normativa/NB-1225003-1.pdf` pesa mas de 100 MB y no se incluye en GitHub para evitar rechazo del push. Si lo necesitas, colocalo manualmente en esa ruta dentro del proyecto local.
