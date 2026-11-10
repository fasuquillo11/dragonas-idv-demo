"""Motor de la proyección para la próxima sesión.

ATENCIÓN METODOLÓGICA: coeficientes OLS estimados EXCLUSIVAMENTE sobre
observaciones y etiquetas generadas artificialmente en 2026. No representan
un modelo validado ni estiman riesgo médico real. Reemplazar al entrenar con
los datos institucionales autorizados y validación temporal.
"""
from __future__ import annotations
from datetime import date, timedelta
import pandas as pd
import numpy as np

COL = {
    'nombre':'Nombre_jugadora', 'fecha':'Fecha',
    'prox':'Fecha_proxima_sesion',
    'feel':'Cómo te sientes previo al entrenamiento',
    'sleep':'Estado de sueño', 'stress':'Tipo de estrés',
    'fatigue':'Tipo de fatiga', 'soreness':'Dolor muscular',
    'hydration':'Nivel de deshidratación',
    'rpe':'RPE_diario','minutes':'Time_total(min)','load':'Load_total',
}
CAT_CODES = {
    COL['feel']: {'Alegre':0, 'Normal':1, 'Nervioso':2, 'Desanimado':3, 'Triste':4},
    COL['sleep']: {'Muy Bueno':0, 'Bueno':1, 'Regular':2, 'Malo':3, 'Muy Malo':4},
    COL['stress']: {'Muy Bajo':0, 'Bajo':1, 'Normal':2, 'Alto':3},
    COL['fatigue']: {'Muy Bajo':0, 'Bajo':1, 'Normal':2, 'Alto':3, 'Muy Alto':4},
    COL['soreness']: {'Muy Bajo':0, 'Bajo':1, 'Normal':2, 'Alto':3, 'Muy Alto':4},
    COL['hydration']: {'Hidratada':0, 'Deshidratada':1, 'Severamente Deshidratada':2},
}
NUMERIC = [COL['rpe'], COL['minutes'], COL['load']]
DAILY_COLUMNS = [COL['fecha'],COL['prox'],COL['nombre'],*CAT_CODES,*NUMERIC]
MODEL_TERMS = [
    'fatiga_actual','sueno','estres','dolor','deshidratacion',
    'sensacion','rpe','carga_centenas','carga_media_7d_centenas',
]
# Se reemplazan por coeficientes OLS calculados con datos sintéticos 2026.
OLS_INTERCEPT = 94.62191
OLS_COEFFICIENTS = {
    'fatiga_actual': -2.72673,
    'sueno': -2.36435,
    'estres': -1.34666,
    'dolor': -1.81366,
    'deshidratacion': -2.15445,
    'sensacion': -2.04324,
    'rpe': -0.65444,
    'carga_centenas': -0.96736,
    'carga_media_7d_centenas': -0.21985,
}


def _day(value):
    ts = pd.to_datetime(value, errors='coerce', dayfirst=False)
    if pd.isna(ts):
        raise ValueError(f'Fecha inválida: {value!r}')
    return ts.date()


def roster(history:pd.DataFrame)->list[str]:
    return sorted(history[COL['nombre']].dropna().astype(str).unique())


def _value_or_default(value, others, numeric=False):
    if pd.notna(value) and str(value).strip():
        return value
    series = pd.Series(others).dropna()
    if series.empty:
        return 0 if numeric else None
    if numeric:
        nums = pd.to_numeric(series, errors='coerce').dropna()
        return float(nums.median()) if not nums.empty else 0.0
    return series.mode().iloc[0]


def complete_record(raw:dict, history:pd.DataFrame)->tuple[dict, int]:
    """Imputa valores faltantes de entrada usando medianas/modas anteriores a t.

    Primero usa el historial previo de la jugadora; si es insuficiente,
    utiliza el del equipo antes de t. Nunca consulta registros posteriores.
    """
    name = str(raw.get(COL['nombre'], '')).strip()
    if name not in roster(history):
        raise ValueError(f'Jugadora no incluida en el plantel ficticio: {name or "(sin nombre)"}')
    d = _day(raw.get(COL['fecha']))
    history_dates = pd.to_datetime(history[COL['fecha']], errors='coerce').dt.date
    earlier = history[history_dates < d]
    player = earlier[earlier[COL['nombre']] == name]
    filled = {COL['nombre']:name, COL['fecha']:d.isoformat()}
    target = raw.get(COL['prox'])
    target_day = _day(target) if pd.notna(target) and str(target).strip() else d + timedelta(days=1)
    if target_day <= d:
        raise ValueError(f'Próxima sesión debe ser posterior a {d}: {name}')
    filled[COL['prox']] = target_day.isoformat()
    imputed = 0
    for field in list(CAT_CODES) + NUMERIC:
        value = raw.get(field)
        if pd.isna(value) or str(value).strip()=='' or str(value).lower()=='nan':
            observed = player[field].dropna() if field in player else pd.Series(dtype=object)
            if observed.empty:
                observed = earlier[field].dropna() if field in earlier else pd.Series(dtype=object)
            value = _value_or_default(None, observed, numeric=field in NUMERIC)
            imputed += 1
        if field in NUMERIC:
            try:
                value = float(str(value).replace(',','.'))
            except Exception:
                raise ValueError(f'{name}: valor no numérico en {field}')
            if not np.isfinite(value) or value < 0:
                raise ValueError(f'{name}: valor inválido en {field}')
        elif value not in CAT_CODES[field]:
            raise ValueError(f'{name}: categoría inválida en {field}: {value}')
        filled[field] = value
    # Si carga fue omitida pero se dieron RPE y duración, calcular por producto;
    # la combinación solo es válida cuando se trata de una sesión.
    if (pd.isna(raw.get(COL['load'])) or str(raw.get(COL['load'])).strip() == '') and pd.notna(raw.get(COL['rpe'])) and pd.notna(raw.get(COL['minutes'])):
        filled[COL['load']] = filled[COL['rpe']] * filled[COL['minutes']]
        imputed = max(0, imputed - 1)
    if not 1 <= filled[COL['rpe']] <= 10:
        raise ValueError(f'{name}: RPE fuera de 1 a 10')
    if not 0 < filled[COL['minutes']] <= 1440:
        raise ValueError(f'{name}: duración fuera de rango')
    return filled, imputed


def _features(row:dict, history:pd.DataFrame)->dict:
    name = row[COL['nombre']]; day = _day(row[COL['fecha']])
    h = history[history[COL['nombre']].eq(name)].copy()
    h['_day'] = pd.to_datetime(h[COL['fecha']], errors='coerce').dt.date
    start = day - timedelta(days=6)
    h = h[h['_day'].between(start,day-timedelta(days=1))]
    loads = pd.to_numeric(h[COL['load']], errors='coerce').dropna().tolist()
    loads.append(float(row[COL['load']]))
    meanload = float(np.mean(loads))
    return {
        'fatiga_actual': CAT_CODES[COL['fatigue']][row[COL['fatigue']]],
        'sueno': CAT_CODES[COL['sleep']][row[COL['sleep']]],
        'estres': CAT_CODES[COL['stress']][row[COL['stress']]],
        'dolor': CAT_CODES[COL['soreness']][row[COL['soreness']]],
        'deshidratacion': CAT_CODES[COL['hydration']][row[COL['hydration']]],
        'sensacion': CAT_CODES[COL['feel']][row[COL['feel']]],
        'rpe': float(row[COL['rpe']]),
        'carga_centenas': float(row[COL['load']])/100,
        'carga_media_7d_centenas': meanload/100,
    }


def compute_forecast(raw:dict,history:pd.DataFrame)->tuple[dict,dict]:
    completed, imputed=complete_record(raw,history)
    features=_features(completed,history)
    # Regresión lineal múltiple ajustada con historia FICTICIA.
    # Bienestar_(t+1) = intercepto + suma(beta_i * x_i(t)); se limita a 0..100.
    wellness=float(np.clip(OLS_INTERCEPT + sum(OLS_COEFFICIENTS[k]*features[k] for k in MODEL_TERMS),0,100))
    # Clasificación provisional por puntuación; NO es un clasificador validado.
    risk=(1.00*features['fatiga_actual'] + .55*features['sueno'] +
          .38*features['estres'] + .55*features['dolor'] +
          .65*features['deshidratacion'] + .21*features['rpe']+
          .12*features['carga_centenas'])
    fatigue='BAJA' if risk<4.15 else 'MODERADA' if risk<6.6 else 'ALTA'
    result={
        'Jugadora':completed[COL['nombre']],
        'Fecha de registro':completed[COL['fecha']],
        'Próxima sesión':completed[COL['prox']],
        'Bienestar previsto':round(wellness,1),
        'Fatiga prevista':fatigue,
        'Variables completadas':imputed,
    }
    return result,completed


def forecast_latest(history:pd.DataFrame, next_session:date)->pd.DataFrame:
    """Vista de equipo, basada en el último registro por jugadora."""
    if history.empty:
        return pd.DataFrame()
    hist=history.copy();hist['_day']=pd.to_datetime(hist[COL['fecha']]).dt.date
    hist=hist[hist['_day']<next_session]
    latest=hist.sort_values('_day').drop_duplicates(COL['nombre'],keep='last')
    out=[]
    for _,r in latest.iterrows():
        record=r.to_dict();record[COL['prox']]=next_session.isoformat()
        try:
            result,_=compute_forecast(record,hist)
            out.append(result)
        except ValueError:
            pass
    return pd.DataFrame(out).sort_values('Jugadora') if out else pd.DataFrame()
