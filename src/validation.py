"""Validadores de entradas. Sin diagnóstico ni interpretación clínica."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from numbers import Real
import math
import re

from .schema import CATEGORIES, DATE_FIELD, INTEGER_FIELDS, NUMERIC_FIELDS, NUMERIC_RANGES

PLAYER_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{3,32}$")


def parse_date(value) -> date | None:
    """Acepta fecha, timestamp pandas, texto ISO y serial Excel."""
    if value is None:
        return None
    if hasattr(value, "to_pydatetime"):
        value = value.to_pydatetime()
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, Real) and not isinstance(value, bool):
        if not math.isfinite(value) or not (10000 < value < 100000):
            return None
        return date(1899, 12, 30) + timedelta(days=int(value))
    if isinstance(value, str):
        v = value.strip()
        if not v:
            return None
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(v, fmt).date()
            except ValueError:
                continue
    return None


def validate_record(record: dict, *, require_player: bool = True,
                    forbid_future: bool = False) -> tuple[dict, list[str], list[str]]:
    """Retorna (registro normalizado, errores, advertencias)."""
    cleaned = dict(record)
    errors: list[str] = []
    warnings: list[str] = []
    player_id = cleaned.get("jugadora_id")
    if require_player and not PLAYER_ID_PATTERN.fullmatch(str(player_id or "")):
        errors.append("ID de jugadora inválido: 3–32 caracteres alfanuméricos, '-' o '_'.")

    d = parse_date(cleaned.get(DATE_FIELD))
    if d is None:
        errors.append("La fecha es obligatoria y debe ser válida.")
    else:
        cleaned[DATE_FIELD] = d.isoformat()
        if d > date.today():
            msg = f"La fecha {d} es posterior al día actual. Revisar origen de datos."
            (errors if forbid_future else warnings).append(msg)

    for field, categories in CATEGORIES.items():
        val = cleaned.get(field)
        if val is None or (isinstance(val, str) and not val.strip()):
            cleaned[field] = None
            continue
        if not isinstance(val, str) or val.strip() not in categories:
            errors.append(f"'{field}': categoría no permitida: {str(val)[:40]}.")
        else:
            cleaned[field] = val.strip()

    for field in NUMERIC_FIELDS:
        value = cleaned.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            cleaned[field] = None
            continue
        try:
            n = float(str(value).strip().replace(",", "."))
            if not math.isfinite(n):
                raise ValueError("No finito")
        except (ValueError, TypeError):
            errors.append(f"'{field}': debe contener un número válido.")
            continue
        lo, hi = NUMERIC_RANGES[field]
        if n < lo or n > hi:
            # En datos históricos identificamos el dato sospechoso, sin descartarlo.
            if forbid_future:
                errors.append(f"'{field}': fuera del rango técnico permitido [{lo:g}, {hi:g}].")
            else:
                warnings.append(f"'{field}': {n:g} fuera del rango técnico [{lo:g}, {hi:g}].")
        if field in INTEGER_FIELDS and not n.is_integer():
            errors.append(f"'{field}': debe ser un número entero.")
        cleaned[field] = int(n) if n.is_integer() else n

    # No forzar Load_total == RPE_diario * tiempo cuando hay múltiples sesiones.
    rpe, dur, load, n_sessions = (cleaned.get(k) for k in
        ("RPE_diario", "Time_total(min)", "Load_total", "Numero_sesiones"))
    if rpe is not None and dur is not None and load is not None and n_sessions == 1:
        if abs(load - rpe * dur) > max(5, 0.05 * max(1, rpe * dur)):
            warnings.append("Revisar Load_total: difiere de RPE_diario × duración en una sesión.")

    return cleaned, errors, warnings
