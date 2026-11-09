"""Contrato entre Excel y el importador, derivado de las columnas de Base_Limpia."""
from .schema import FIELD_GROUPS, CATEGORIES

SHEETS = ("JUGADORAS", "DIARIO", "EVALUACIONES")
PLAYER_COLUMNS = ["ID_jugadora", "Nombre_jugadora", "Posición"]
DAILY_GROUPS = ["Identificación", "Wellness diario", "Carga de entrenamiento", "GPS"]
PERIODIC_GROUPS = ["Evaluaciones clínicas", "Evaluaciones neuromusculares"]
DAILY_FIELDS = [f for g in DAILY_GROUPS for f in FIELD_GROUPS[g] if f != 'Posición']
PERIODIC_FIELDS = [f for g in PERIODIC_GROUPS for f in FIELD_GROUPS[g]]
DAILY_COLUMNS = ["Fecha", "ID_jugadora", *DAILY_FIELDS]
PERIODIC_COLUMNS = ["Fecha", "ID_jugadora", *PERIODIC_FIELDS]
ALL_FEATURES = set(DAILY_FIELDS + PERIODIC_FIELDS)
assert len(ALL_FEATURES) == 40
