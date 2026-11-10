"""Especificación de Excel por fuente de información, alineada con Base_Limpia.

La plantilla original JUGADORAS/DIARIO/EVALUACIONES se sigue leyendo por compatibilidad.
"""
from .schema import FIELD_GROUPS

PLAYER_COLUMNS = ["ID_jugadora", "Nombre_jugadora", "Posición"]
SOURCE_FIELDS = {
    "WELLNESS": ["Peso en ayunas (kg)", *FIELD_GROUPS["Wellness diario"]],
    "ENTRENAMIENTO": list(FIELD_GROUPS["Carga de entrenamiento"]),
    "GPS": list(FIELD_GROUPS["GPS"]),
    "CLINICA": list(FIELD_GROUPS["Evaluaciones clínicas"]),
    "NEUROMUSCULAR": list(FIELD_GROUPS["Evaluaciones neuromusculares"]),
}
SHEETS = ("JUGADORAS", *SOURCE_FIELDS.keys())
SOURCE_COLUMNS = {name: ["Fecha", "ID_jugadora", *fields] for name, fields in SOURCE_FIELDS.items()}
DAILY_SOURCE_SHEETS = ("WELLNESS", "ENTRENAMIENTO", "GPS")
PERIODIC_SOURCE_SHEETS = ("CLINICA", "NEUROMUSCULAR")
DAILY_FIELDS = [f for sheet in DAILY_SOURCE_SHEETS for f in SOURCE_FIELDS[sheet]]
PERIODIC_FIELDS = [f for sheet in PERIODIC_SOURCE_SHEETS for f in SOURCE_FIELDS[sheet]]
DAILY_COLUMNS = ["Fecha", "ID_jugadora", *DAILY_FIELDS]
PERIODIC_COLUMNS = ["Fecha", "ID_jugadora", *PERIODIC_FIELDS]
ALL_FEATURES = set(DAILY_FIELDS + PERIODIC_FIELDS)
assert len(ALL_FEATURES) == 40 and not (set(DAILY_FIELDS) & set(PERIODIC_FIELDS))

# Plantillas independientes para actualizaciones incrementales. Una fuente sin
# archivo nuevo NO genera altas, cambios, bajas ni imputaciones.
UPDATE_SOURCES = {
    "GPS": {"label": "GPS", "sheet": "GPS", "fields": SOURCE_FIELDS["GPS"], "destination": "diario",
            "filename": "Plantilla_GPS.xlsx", "description": "Distancias, velocidades, sprints y aceleraciones."},
    "WELLNESS_CARGA": {"label": "Wellness y Carga", "sheet": "WELLNESS_CARGA",
                       "fields": SOURCE_FIELDS["WELLNESS"] + SOURCE_FIELDS["ENTRENAMIENTO"],
                       "destination": "diario", "filename": "Plantilla_Wellness_y_Carga.xlsx",
                       "description": "Cuestionario de bienestar, RPE, duración y carga de entrenamiento."},
    "BIOMECANICOS": {"label": "Biomecánicos", "sheet": "BIOMECANICOS",
                     "fields": SOURCE_FIELDS["NEUROMUSCULAR"], "destination": "evaluaciones",
                     "filename": "Plantilla_Biomecanicos.xlsx", "description": "Fuerza, torque y pruebas de salto."},
    "LABORATORIO": {"label": "Laboratorio", "sheet": "LABORATORIO",
                    "fields": SOURCE_FIELDS["CLINICA"], "destination": "evaluaciones",
                    "filename": "Plantilla_Laboratorio.xlsx", "description": "Parámetros de laboratorio en su fecha real de medición."},
}
UPDATE_ID_COLUMNS = ["Fecha", "Nombre_jugadora"]
UPDATE_SOURCE_COLUMNS = {key: [*UPDATE_ID_COLUMNS, *spec["fields"]]
                         for key, spec in UPDATE_SOURCES.items()}
assert len(set(f for spec in UPDATE_SOURCES.values() for f in spec['fields'])) == 40
