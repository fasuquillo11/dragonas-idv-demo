# DRAGONAS | Panel de bienestar y fatiga de la próxima sesión

Interfaz de apariencia final con **datos 100 % sintéticos** para 2026. Modelo de regresión lineal ajustado sobre etiquetas sintéticas, no sobre datos del club. La clasificación de fatiga también es provisional. No se debe utilizar para selección de jugadoras ni decisiones clínicas.

## Qué hace

- **Inicio**: dashboard de 24 jugadoras con nombres ficticios, estado por jugadora, carga semanal, fatiga proyectada y exportación del historial sintético.
- **Simulador**: ingresar **una o cualquier cantidad de filas** en una tabla editable, o descargar/subir un Excel con 1 o 10 filas; pulsar **Predecir próxima sesión** y obtener una predicción individual de bienestar y fatiga para cada fila. Descargar resultados en `.xlsx`.
- **Registro de simulaciones**: filtrar y descargar el historial generado durante la sesión del navegador.

Las fechas son por fila: `Fecha` (datos de hoy) y `Fecha_proxima_sesion` (si se omite se usa el día siguiente como supuesto, no el calendario real de entrenamientos). Si se deja un campo sin medir se completa mediante la mediana o la moda de registros históricos previos de esa jugadora; si no existen, se usa el equipo. Si se informa RPE y duración pero no carga, se calcula `RPE × duración`.

El motor numérico está en `src/forecast.py`: intercepto, coeficientes estimados con mínimos cuadrados sintéticos y ecuación de regresión explícita. Las categorías de fatiga se asignan mediante un puntaje provisional. No se afirma que el algoritmo esté entrenado o validado con datos reales.

`data/historial_ficticio_2026.csv` permite que el dashboard cargue inmediatamente. `data/Dragonas_Datos_Ficticios_2026.xlsx` contiene las hojas `HISTORIAL_2026`, `GPS_2026`, `BIOMECANICOS_2026`, `LABORATORIO_2026`, `REGISTROS_HOY` y `METODOLOGIA`. Contiene **2112** registros diarios y **24** nombres inventados. Valores faltantes artificiales completados por medianas/modas de cada jugadora.

`plantillas/Plantilla_1_jugadora.xlsx` y `plantillas/Plantilla_10_jugadoras.xlsx` sirven para probar ambas cargas. `plantillas/` también conserva las cuatro plantillas independientes por fuente.

## Uso y despliegue

Subir **el contenido** del ZIP a la raíz de GitHub, conservando `app.py`, `requirements.txt`, `src/forecast.py`, `data/`, `plantillas/` y `.streamlit/config.toml`. El repositorio puede mantener archivos antiguos que ya no se importan. En Streamlit Community Cloud: branch `main`, archivo principal `app.py`.

**Seguridad:** Esta instancia pública admite solo los 24 nombres ficticios definidos en el CSV. La carga de Excel y la edición se limitan a ese plantel sintético; nunca introducir datos identificables o clínicos reales. Los registros editados se guardan solo en `st.session_state` y se pierden al reiniciar la sesión del navegador. La versión médica real requiere autenticación, almacenamiento cifrado/autorizado y modelos validados.
