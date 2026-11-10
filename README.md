# Dragonas IDV/USFQ — Dashboard y simulador · Versión 5

Demo académica en Streamlit. **No es un modelo entrenado o validado.** Los resultados son artificiales y no deben usarse para decisiones de participación, fatiga o atención médica.

## Navegación

- **Inicio · Dashboard**: objetivo, resumen de cobertura por las cuatro fuentes y simulaciones recientes.
- **Simulador**: cuatro descargas independientes para actualizaciones por fuente, selección de jugadora y fecha, simulación ficticia y descarga del resultado CSV.
- **Registro de simulaciones**: filtros, historial y exportación CSV.

## Plantillas independientes

La carpeta `plantillas/` contiene:

| Fuente mostrada | Archivo | Hoja de captura | Campos |
| --- | --- | --- | --- |
| GPS | `Plantilla_GPS.xlsx` | `GPS` | Distancias, velocidades, sprints y aceleraciones |
| Wellness y Carga | `Plantilla_Wellness_y_Carga.xlsx` | `WELLNESS_CARGA` | Cuestionario, peso, RPE, duración y carga |
| Biomecánicos | `Plantilla_Biomecanicos.xlsx` | `BIOMECANICOS` | Fuerza, torque, CMJ y RSI |
| Laboratorio | `Plantilla_Laboratorio.xlsx` | `LABORATORIO` | Hemoglobina, hematocrito, ferritina, cortisol, testosterona y CPK |

Cada archivo tiene una hoja de captura (primera) y otra de instrucciones. **Fecha** y **Nombre_jugadora** identifican provisionalmente cada observación. **No se solicita ID de jugadora**. Los nombres deben escribirse igual en todas las fuentes. Si hay homónimas, deben resolverse antes de importar.

**Regla de actualización incremental**: si no se carga un archivo para una fuente, **NO se modifica esa fuente**. Las celdas vacías no borran valores previos ni se interpretan como ceros. Los registros de distintas fuentes se unen por `(Nombre_jugadora, Fecha)` cuando corresponden a la misma tabla. Las mediciones periódicas conservan su fecha original. El importador (`read_source_updates`) revisa encabezados, categorías, formatos, duplicados y conflictos; `apply_source_updates` aplica el lote de manera transaccional, sin sobrescribir un valor histórico incompatible.

El formato antiguo con ID solo se conserva como compatibilidad interna; **la interfaz y las cuatro plantillas nuevas no lo solicitan**. La identificación definitiva se diseñará más adelante.

## Seguridad y despliegue

**La demo pública NO permite importar Excel**. Puede mostrar y descargar las cuatro plantillas vacías. No debe alojar datos reales, nombres ni archivos médicos. En `app.py`, `PRIVATE=False` es intencional: no lo cambies a `True` para usar el entorno público. La activación de subida real requiere antes una instalación privada con autenticación, autorización institucional, base de datos protegida y persistente y controles de acceso. El SQLite de Streamlit Community Cloud es efímero y no es apto como repositorio clínico.

Para actualizar GitHub, descomprimir y subir en la raíz del repositorio `app.py`, `README.md`, `requirements.txt`, la carpeta **`src/` completa** y la carpeta **`plantillas/` completa**. Conservar la estructura de directorios. La carpeta `.streamlit/`, si se sube, es opcional.

Para pruebas del código de importación, los cuatro archivos de entrada pueden procesarse a la vez o en distintos momentos. Si ninguno se proporciona, no se modifica ningún registro. Los archivos vacíos tampoco cambian el historial.
