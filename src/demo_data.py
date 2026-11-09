"""Datos completamente sintéticos para prueba; no representan a Dragonas."""
from __future__ import annotations
from datetime import date, timedelta
from random import Random


def make_demo_records() -> list[dict]:
    rng = Random(81121)
    records = []
    start = date(2026, 9, 1)
    for p in range(1, 9):
        for i in range(30):
            if i % 7 == 0:
                continue
            rpe = rng.randint(2, 8)
            duration = rng.choice((45, 60, 75, 90))
            record = {
                "jugadora_id": f"DEMO-{p:02d}",
                "Fecha": (start + timedelta(days=i)).isoformat(),
                "Posición": rng.choice(["Defensa Central", "Interior", "Extremo", "Arquera"]),
                "Cómo te sientes previo al entrenamiento": rng.choice(["Normal", "Alegre", "Normal"]),
                "Estado de sueño": rng.choice(["Bueno", "Muy Bueno", "Regular"]),
                "Tipo de estrés": rng.choice(["Bajo", "Normal", "Muy Bajo"]),
                "Tipo de fatiga": rng.choice(["Bajo", "Normal", "Alto"]),
                "Dolor muscular": rng.choice(["Bajo", "Normal", "Alto"]),
                "Nivel de deshidratación": "Hidratada",
                "RPE_diario": rpe,
                "RPE_max": rpe,
                "Load_total": rpe * duration,
                "Time_total(min)": duration,
                "Numero_sesiones": 1,
                "Distancia total (m)": rng.randint(1700, 8000) if i % 3 != 0 else None,
            }
            records.append(record)
    return records
