"""Exportaciones CSV compatibles con Excel, sin datos clínicos reales en demo."""
from __future__ import annotations
import csv
from io import StringIO

RESULT_COLUMNS = ["Jugadora", "Fecha de datos", "Fecha objetivo",
                  "Bienestar DEMO", "Fatiga DEMO", "Versión"]


def export_csv(rows):
    output = StringIO()
    output.write('\ufeff')  # BOM: Excel reconoce tildes en UTF-8
    writer = csv.DictWriter(output, fieldnames=RESULT_COLUMNS, extrasaction='ignore', delimiter=';')
    writer.writeheader()
    for row in rows:
        writer.writerow({key: row.get(key, '') for key in RESULT_COLUMNS})
    return output.getvalue().encode('utf-8')


def result_to_row(result, player_id, player_name):
    return {
        'Jugadora': player_name,
        'Fecha de datos': result['fecha_datos'],
        'Fecha objetivo': result['fecha_objetivo'],
        'Bienestar DEMO': result['bienestar_demo'],
        'Fatiga DEMO': result['fatiga_demo'],
        'Versión': result['version'],
    }
