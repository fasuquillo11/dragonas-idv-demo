"""Esquema derivado de las 43 columnas de Base_Limpia.xlsx.

Los umbrales de control son TÉCNICOS, NO CLÍNICOS y deben revisarse
antes de cualquier despliegue institucional.
"""
from __future__ import annotations

DATE_FIELD = "Fecha"
NAME_FIELD = "Nombre_Limpio"

FIELD_GROUPS = {
    "Identificación": [
        "Posición", "Peso en ayunas (kg)",
    ],
    "Wellness diario": [
        "Cómo te sientes previo al entrenamiento", "Estado de sueño",
        "Tipo de estrés", "Tipo de fatiga", "Dolor muscular",
        "Nivel de deshidratación",
    ],
    "Carga de entrenamiento": [
        "RPE_diario", "RPE_max", "Load_total", "Time_total(min)",
        "Numero_sesiones",
    ],
    "GPS": [
        "Distancia total (m)", "Metros por minuto (m/min)",
        "Distancia recorrida a alta velocidad (m)", "Velocidad máxima (km/h)",
        "Esfuerzos de aceleración promedio B1-B3",
        "Esfuerzos de desaceleración promedio B1-B3",
        "Distancia a 14-17 km/h (m)", "Distancia a 17-21 km/h (m)",
        "Distancia a 21-25 km/h (m)", "Vel B7 Tot Dist (m)",
        "Aceleraciones + desaceleraciones", "Esfuerzos de sprint",
    ],
    "Evaluaciones clínicas": [
        "Hemoglobina (g/dL)", "Hematocrito (%)", "Ferritina",
        "Cortisol (ug/dL)", "Testosterona (ng/mL)", "CPK (U/L)",
    ],
    "Evaluaciones neuromusculares": [
        "Nordic Fuerza Promedio Izquierda (N)",
        "Nordic Fuerza Promedio Derecha (N)",
        "Nordic Torque Máximo Izquierda (Nm)",
        "Nordic Torque Máximo Derecha (Nm)",
        "ISO Prone Fuerza Máxima Izquierda (N)",
        "ISO Prone Fuerza Máxima Derecha (N)",
        "Knee Extension Pull Fuerza Máxima Izquierda (N)",
        "Knee Extension Pull Fuerza Máxima Derecha (N)",
        "CMJ Altura de Salto por Impulso Momento (cm)",
        "CMJ RSI Modificado (m/s)",
    ],
}

CATEGORIES = {
    "Cómo te sientes previo al entrenamiento": [
        "Normal", "Alegre", "Desanimado", "Nervioso", "Triste",
    ],
    "Estado de sueño": ["Muy Bueno", "Bueno", "Regular", "Malo", "Muy Malo"],
    "Tipo de estrés": ["Muy Bajo", "Bajo", "Normal", "Alto"],
    "Tipo de fatiga": ["Muy Bajo", "Bajo", "Normal", "Alto", "Muy Alto"],
    "Dolor muscular": ["Muy Bajo", "Bajo", "Normal", "Alto", "Muy Alto"],
    "Nivel de deshidratación": [
        "Hidratada", "Deshidratada", "Severamente Deshidratada",
    ],
    "Posición": [
        "Interior", "Extremo", "Delantero", "Defensa Lateral",
        "Defensa Central", "Arquera", "Medio Centro",
    ],
}

COLUMNS = [DATE_FIELD, NAME_FIELD]
for fields in FIELD_GROUPS.values():
    for field in fields:
        if field not in COLUMNS:
            COLUMNS.append(field)

# Los nombres de las columnas originales se conservan salvo espacios finales.
NUMERIC_FIELDS = [c for c in COLUMNS if c not in (DATE_FIELD, NAME_FIELD) and c not in CATEGORIES]

# Límites lógicos / de formato para impedir errores mecánicos de entrada.
# No son intervalos normales ni cortes médicos.
NUMERIC_RANGES = {field: (0, 1_000_000) for field in NUMERIC_FIELDS}
NUMERIC_RANGES.update({
    "RPE_diario": (1, 10),
    "RPE_max": (1, 10),
    "Time_total(min)": (0, 1440),
    "Numero_sesiones": (0, 10),
    "Peso en ayunas (kg)": (20, 200),
    "CMJ Altura de Salto por Impulso Momento (cm)": (0, 150),
    "CMJ RSI Modificado (m/s)": (0, 10),
    "Hematocrito (%)": (0, 100),
    "Velocidad máxima (km/h)": (0, 60),
    "Metros por minuto (m/min)": (0, 500),
})
INTEGER_FIELDS = {
    "Numero_sesiones", "Esfuerzos de sprint",
    "Esfuerzos de aceleración promedio B1-B3",
    "Esfuerzos de desaceleración promedio B1-B3",
    "Aceleraciones + desaceleraciones",
}

# Alertas de auditoría. El archivo REAL contiene algunos de estos casos;
# nunca se corrigen automáticamente ni se interpretan clínicamente.
QUALITY_CHECKS = {
    "Peso en ayunas (kg)": (20, 200),
    "CMJ Altura de Salto por Impulso Momento (cm)": (0, 150),
    "RPE_diario": (1, 10),
    "RPE_max": (1, 10),
    "Time_total(min)": (0, 1440),
    "Hematocrito (%)": (0, 100),
}

assert len(COLUMNS) == 43, f"Se esperaban 43 columnas, hay {len(COLUMNS)}"
