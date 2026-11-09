"""Preparación temporal de inputs; no ejecuta ML ni imputa la variable objetivo.

Solo observaciones con fecha <= t. Las reglas de vigencia son configurables,
provisionales y DEBEN COINCIDIR con el entrenamiento futuro.
"""
from __future__ import annotations
from datetime import date, timedelta
from .template_spec import DAILY_FIELDS, PERIODIC_FIELDS
from .schema import FIELD_GROUPS

CLINICAL=set(FIELD_GROUPS['Evaluaciones clínicas'])
NEURO=set(FIELD_GROUPS['Evaluaciones neuromusculares'])

def snapshot(player, day, daily, periodic, *, clinical_max_days=90, neuro_max_days=60):
    d=date.fromisoformat(day)
    cur=next((r for r in daily if r['jugadora_id']==player and r['Fecha']==day),None)
    values={};audit=[]
    for f in DAILY_FIELDS:
        value=cur.get(f) if cur else None
        values[f]=value
        audit.append({'Variable':f,'Valor utilizado':value,'Procedencia':'Medido ese día' if value is not None else 'Sin medición diaria','Fecha origen':day if value is not None else None,'Antigüedad (días)':0 if value is not None else None})
    candidates=[r for r in periodic if r['jugadora_id']==player and date.fromisoformat(r['Fecha'])<=d]
    candidates.sort(key=lambda r:r['Fecha'],reverse=True)
    for f in PERIODIC_FIELDS:
        previous=next((r for r in candidates if r.get(f) is not None),None)
        age=(d-date.fromisoformat(previous['Fecha'])).days if previous else None
        expiry=clinical_max_days if f in CLINICAL else neuro_max_days
        if previous is None:
            val=None;status='Sin medición histórica'
        elif age>expiry:
            val=None;status='Medición anterior fuera de vigencia DEMO'
        elif age==0:
            val=previous[f];status='Medido ese día'
        else:
            val=previous[f];status='Última medición previa (vigencia DEMO)'
        values[f]=val
        audit.append({'Variable':f,'Valor utilizado':val,'Procedencia':status,
                      'Fecha origen':previous['Fecha'] if previous else None,'Antigüedad (días)':age})
    windows={}
    for n in (3,7,14,28):
        start=d-timedelta(days=n-1)
        rows=[r for r in daily if r['jugadora_id']==player and start<=date.fromisoformat(r['Fecha'])<=d]
        measured=[float(r['Load_total']) for r in rows if r.get('Load_total') is not None]
        windows[f'carga_observada_{n}d']=round(sum(measured),2) if measured else None
        windows[f'dias_con_carga_{n}d']=len(measured)
        windows[f'cobertura_{n}d']=round(100*len(measured)/n,1)
    return {'jugadora_id':player,'Fecha':day,'valores':values,'auditoria':audit,'ventanas':windows,
            'reglas_demo':{'clínica_días':clinical_max_days,'neuromuscular_días':neuro_max_days},
            'hay_registro_diario':cur is not None}
