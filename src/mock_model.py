"""Simulador de demostración (NO ES ML, NO ESTÁ ENTRENADO).

Retirar la clase al conectar pipelines reales. No usar para planificación,
selección de jugadoras ni decisiones sanitarias.
"""
from __future__ import annotations

from datetime import date, timedelta

VERSION = "DEMO_REGLAS_V1_NO_VALIDADO"

WEIGHTS = {
    "Tipo de fatiga": {"Muy Bajo": 0, "Bajo": 1, "Normal": 2, "Alto": 3, "Muy Alto": 4},
    "Estado de sueño": {"Muy Bueno": 0, "Bueno": .5, "Regular": 1.5, "Malo": 2.3, "Muy Malo": 3},
    "Dolor muscular": {"Muy Bajo": 0, "Bajo": .5, "Normal": 1, "Alto": 2, "Muy Alto": 3},
    "Tipo de estrés": {"Muy Bajo": 0, "Bajo": .3, "Normal": 1, "Alto": 2},
    "Nivel de deshidratación": {"Hidratada": 0, "Deshidratada": 1.5,
                                  "Severamente Deshidratada": 3},
    "Cómo te sientes previo al entrenamiento": {
        "Alegre": 0, "Normal": .3, "Nervioso": 1,
        "Desanimado": 2, "Triste": 2,
    },
}


def last_loads(records: list[dict], player: str, t: str, days: int = 28) -> dict:
    end = date.fromisoformat(t)
    start = end - timedelta(days=days-1)
    rows = [r for r in records if r["jugadora_id"] == player and start <=
            date.fromisoformat(r["Fecha"]) <= end]
    valid = [float(r["Load_total"]) for r in rows if r.get("Load_total") is not None]
    return {
        "ventana_dias": days,
        "registros_en_ventana": len(rows),
        "dias_con_carga": len(valid),
        "suma_carga_observada": round(sum(valid), 2) if valid else None,
        "cobertura_diaria": round(len(valid) / days * 100, 1),
        "nota": "Los días sin medición NO se reemplazan por carga cero.",
    }


def demo_predict(record: dict, history: list[dict]) -> dict:
    """Resultado FICTICIO 0-100 y clases; sirve para probar la interfaz."""
    for mandatory in ("Tipo de fatiga", "Estado de sueño"):
        if record.get(mandatory) not in WEIGHTS[mandatory]:
            raise ValueError(f"El simulador necesita '{mandatory}' en el registro de origen.")
    total = 0.0
    detail: dict[str, float] = {}
    factors = {
        "Tipo de fatiga": 6,
        "Estado de sueño": 5,
        "Dolor muscular": 4,
        "Tipo de estrés": 3,
        "Nivel de deshidratación": 4,
        "Cómo te sientes previo al entrenamiento": 3,
    }
    for field, scale in factors.items():
        val = record.get(field)
        if val in WEIGHTS[field]:
            contribution = WEIGHTS[field][val] * scale
            detail[field] = round(contribution, 2)
            total += contribution
    load = record.get("Load_total")
    if load is None and record.get("RPE_diario") is not None and record.get("Time_total(min)") is not None:
        load = float(record["RPE_diario"]) * float(record["Time_total(min)"])
    if load is not None:
        load_part = min(float(load) / 200, 6) * 2
        total += load_part
        detail["Carga actual (contribución demo)"] = round(load_part, 2)
    score = round(max(0, min(100, 92 - total)), 1)
    # Umbrales arbitrarios y transparentes: no tienen fundamento clínico.
    if total >= 33:
        fatigue = "ALTA"
    elif total >= 20:
        fatigue = "MODERADA"
    else:
        fatigue = "BAJA"
    t = date.fromisoformat(record["Fecha"])
    return {
        "tipo": "SIMULACIÓN / NO VALIDADA",
        "version": VERSION,
        "fecha_datos": t.isoformat(),
        "fecha_objetivo": (t + timedelta(days=1)).isoformat(),
        "bienestar_demo": score,
        "fatiga_demo": fatigue,
        "detalle_arbitrario": detail,
        "historico_28d": last_loads(history, record["jugadora_id"], t.isoformat()),
        "carga_en_estimacion": load is not None,
    }
