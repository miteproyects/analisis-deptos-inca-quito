# Analisis de Precios de Departamentos - El Inca / San Isidro del Inca

Aplicacion web interactiva para analizar precios de departamentos en venta en el sector del Inca y San Isidro del Inca, Quito, Ecuador.

## Caracteristicas

- Scraping multi-portal: Properati, Plusvalia, iCasas, Terrenos.com
- Mapa interactivo con radio de busqueda configurable
- Analisis por ano de construccion, area, dormitorios, banos, parqueaderos y piso
- Zona de influencia con analisis de distancia al centro del Inca
- Modulo personalizado: analisis de tu departamento y recomendaciones de venta
- Estrategia de promocion y pricing sugerido

## Despliegue en Streamlit Cloud

1. Sube este repositorio a GitHub
2. Ve a share.streamlit.io
3. Conecta tu repo de GitHub
4. Selecciona app.py como archivo principal
5. Haz clic en Deploy

## Ejecucion local

pip install -r requirements.txt
streamlit run app.py

## Estructura

- app.py - App principal de Streamlit
- scraper.py - Modulo de scraping y generacion de datos
- requirements.txt - Dependencias
- .streamlit/config.toml - Tema y configuracion

## Tecnologias

- Python 3.10+
- Streamlit
- Plotly (graficos interactivos)
- BeautifulSoup4 (web scraping)
- Pandas / NumPy (analisis de datos)
