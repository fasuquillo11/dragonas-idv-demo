"""Interpretación y validación del formato Excel que completará la médica."""
from __future__ import annotations
from io import BytesIO
import re
import pandas as pd
from .schema import CATEGORIES
from .template_spec import (SHEETS, PLAYER_COLUMNS, DAILY_COLUMNS,
                            PERIODIC_COLUMNS, DAILY_FIELDS, PERIODIC_FIELDS)
from .validation import PLAYER_ID_PATTERN, validate_record


def _null(x):
    try:
        if pd.isna(x):return None
    except (TypeError, ValueError): pass
    if isinstance(x,str) and not x.strip():return None
    return x.strip() if isinstance(x,str) else x


def _sheet(xl,sheet,required):
    df=pd.read_excel(xl,sheet_name=sheet)
    df.columns=[str(k).strip() for k in df.columns]
    if len(df.columns)!=len(set(df.columns)):
        raise ValueError(f'Encabezados repetidos en hoja {sheet}.')
    missing=[h for h in required if h not in df.columns]
    if missing:
        raise ValueError(f'En {sheet} faltan columnas: {", ".join(missing[:7])}')
    return df.dropna(how='all').reset_index(drop=True)


def read_template(filename,content,existing_players=None):
    if not filename.lower().endswith('.xlsx'):
        raise ValueError('Debe cargar un archivo .xlsx de la plantilla proporcionada.')
    if len(content)>10*1024*1024:
        raise ValueError('Archivo mayor que 10 MB; dividir los registros.')
    try:
        xl=pd.ExcelFile(BytesIO(content),engine='openpyxl')
    except Exception as exc:
        raise ValueError('No se pudo abrir el archivo Excel.') from exc
    missing=[s for s in SHEETS if s not in xl.sheet_names]
    if missing:raise ValueError('Faltan hojas obligatorias: '+', '.join(missing))
    dfs={
        'JUGADORAS':_sheet(xl,'JUGADORAS',PLAYER_COLUMNS),
        'DIARIO':_sheet(xl,'DIARIO',DAILY_COLUMNS),
        'EVALUACIONES':_sheet(xl,'EVALUACIONES',PERIODIC_COLUMNS),
    }
    report={'filas':{},'validas':{},'errores':[],'avisos':[],'duplicados':0}
    players=[]; seen=set()
    existing={p['jugadora_id']:p['nombre'] for p in (existing_players or [])}
    for idx,row in dfs['JUGADORAS'].iterrows():
        r={c:_null(row.get(c)) for c in PLAYER_COLUMNS}
        pid,nombre,posicion=r['ID_jugadora'],r['Nombre_jugadora'],r['Posición']
        label=f'JUGADORAS fila {idx+2}'
        if not isinstance(pid,str) or not PLAYER_ID_PATTERN.fullmatch(pid):
            report['errores'].append(f'{label}: ID_jugadora inválido (3–32 caracteres, letras/números/_/-).');continue
        if not isinstance(nombre,str) or not (2<=len(nombre)<=120):
            report['errores'].append(f'{label}: nombre obligatorio de 2 a 120 caracteres.');continue
        if pid in seen:
            report['errores'].append(f'{label}: ID repetido en hoja JUGADORAS.');continue
        if posicion is not None and posicion not in CATEGORIES['Posición']:
            report['errores'].append(f'{label}: posición no permitida.');continue
        if pid in existing and existing[pid]!=nombre:
            report['errores'].append(f'{label}: este ID pertenece a otra jugadora en la base.');continue
        seen.add(pid)
        players.append({'jugadora_id':pid,'nombre':nombre,'posicion':posicion})
    valid_ids=seen|set(existing)
    daily=[];periodic=[]
    for sheet,fields,target in [('DIARIO',DAILY_FIELDS,daily),('EVALUACIONES',PERIODIC_FIELDS,periodic)]:
        groups={}
        for idx,row in dfs[sheet].iterrows():
            pid=_null(row.get('ID_jugadora'))
            label=f'{sheet} fila {idx+2}'
            if pid not in valid_ids:
                report['errores'].append(f'{label}: ID_jugadora no existe en JUGADORAS ni en historial.');continue
            candidate={'jugadora_id':pid,'Fecha':_null(row.get('Fecha'))}
            for field in fields:
                candidate[field]=_null(row.get(field))
            cleaned,errors,warnings=validate_record(candidate,forbid_future=True)
            if errors:
                report['errores'].append(f'{label}: '+ '; '.join(errors[:3]));continue
            vals={f:v for f,v in cleaned.items() if f not in ('jugadora_id','Fecha') and v is not None}
            if not vals:
                report['avisos'].append(f'{label}: ningún valor medido; se omite.');continue
            key=cleaned['jugadora_id'],cleaned['Fecha']
            if key in groups:
                previous=groups[key]
                conflicts=[f for f,v in vals.items() if previous.get(f) is not None and previous[f]!=v]
                if conflicts:
                    report['errores'].append(f'{label}: valores incompatibles para mismo ID+fecha en {sheet}: '+', '.join(conflicts[:3]))
                    continue
                previous.update(vals)
                report['duplicados']+=1
                continue
            groups[key]=dict(jugadora_id=key[0],Fecha=key[1],**vals)
            if warnings:
                report['avisos'].append(f'{label}: '+'; '.join(warnings[:3]))
        target.extend(groups.values())
    report['filas']={s:len(df) for s,df in dfs.items()}
    report['validas']={'JUGADORAS':len(players),'DIARIO':len(daily),'EVALUACIONES':len(periodic)}
    report['errores_total']=len(report['errores'])
    report['avisos_total']=len(report['avisos'])
    return players,daily,periodic,report
