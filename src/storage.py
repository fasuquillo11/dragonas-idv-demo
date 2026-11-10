"""Historial SQLite *local*. NO adecuado para alojamiento compartido en la nube.

Se conservan nombres para que la médica pueda identificar jugadoras. El disco
no está cifrado por SQLite, por lo que requiere equipo y copias protegidas.
"""
from __future__ import annotations
import json
import os
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

BASE=Path(__file__).resolve().parents[1]
DB=Path(os.getenv('DRAGONAS_DB_PATH',str(BASE/'data'/'dragonas_registros.sqlite3')))

def connect():
    DB.parent.mkdir(parents=True,exist_ok=True)
    cn=sqlite3.connect(str(DB),timeout=20)
    cn.execute('PRAGMA foreign_keys=ON')
    return cn

def initialize():
    with connect() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS jugadoras (
          jugadora_id TEXT PRIMARY KEY, nombre TEXT NOT NULL, posicion TEXT
        );
        CREATE TABLE IF NOT EXISTS diario (
          jugadora_id TEXT NOT NULL REFERENCES jugadoras(jugadora_id),
          fecha TEXT NOT NULL, valores TEXT NOT NULL, actualizado TEXT NOT NULL,
          PRIMARY KEY (jugadora_id,fecha)
        );
        CREATE TABLE IF NOT EXISTS evaluaciones (
          jugadora_id TEXT NOT NULL REFERENCES jugadoras(jugadora_id),
          fecha TEXT NOT NULL, valores TEXT NOT NULL, actualizado TEXT NOT NULL,
          PRIMARY KEY (jugadora_id,fecha)
        );
        CREATE TABLE IF NOT EXISTS simulaciones (
          id INTEGER PRIMARY KEY, jugadora_id TEXT NOT NULL, fecha TEXT NOT NULL,
          fecha_objetivo TEXT NOT NULL, bienestar_demo REAL NOT NULL,
          fatiga_demo TEXT NOT NULL, version TEXT NOT NULL, creado TEXT NOT NULL
        );
        ''')

def load_players():
    with connect() as c:
        rows=c.execute('SELECT jugadora_id,nombre,posicion FROM jugadoras ORDER BY nombre').fetchall()
    return [dict(zip(['jugadora_id','nombre','posicion'],r)) for r in rows]

def save_players(rows):
    summary={'nuevas':0,'existentes':0,'conflictos_nombre':0}
    with connect() as c:
        for r in rows:
            old=c.execute('SELECT nombre FROM jugadoras WHERE jugadora_id=?',(r['jugadora_id'],)).fetchone()
            if old:
                if old[0] != r['nombre']:
                    summary['conflictos_nombre']+=1  # no reasignar identificador en silencio
                else:
                    summary['existentes']+=1
                    if r.get('posicion'):
                        c.execute('UPDATE jugadoras SET posicion=? WHERE jugadora_id=?',(r['posicion'],r['jugadora_id']))
                continue
            c.execute('INSERT INTO jugadoras VALUES (?,?,?)',(r['jugadora_id'],r['nombre'],r.get('posicion')))
            summary['nuevas']+=1
    return summary

def get_rows(table):
    if table not in ('diario','evaluaciones'):
        raise ValueError('Tabla no permitida')
    with connect() as c:
        rows=c.execute(f'SELECT jugadora_id,fecha,valores FROM {table} ORDER BY fecha,jugadora_id').fetchall()
    return [dict(jugadora_id=p,Fecha=d,**json.loads(payload)) for p,d,payload in rows]

def save_rows(table, rows, *, overwrite_conflicts=False):
    if table not in ('diario','evaluaciones'):
        raise ValueError('Tabla no permitida')
    result={'nuevas':0,'complementadas':0,'sin_cambios':0,'campos_conflictivos':0}
    now=datetime.now(timezone.utc).isoformat()
    with connect() as c:
        for r in rows:
            p,d=r['jugadora_id'],r['Fecha']
            if not c.execute('SELECT 1 FROM jugadoras WHERE jugadora_id=?',(p,)).fetchone():
                raise ValueError(f'Jugadora sin registrar en JUGADORAS: {p}')
            incoming={k:v for k,v in r.items() if k not in ('jugadora_id','Fecha') and v is not None}
            old=c.execute(f'SELECT valores FROM {table} WHERE jugadora_id=? AND fecha=?',(p,d)).fetchone()
            if old:
                obj=json.loads(old[0]); changed=False
                for key,value in incoming.items():
                    if key in obj and obj[key] is not None and obj[key]!=value:
                        result['campos_conflictivos']+=1
                        if not overwrite_conflicts:
                            continue
                    if obj.get(key)!=value:
                        obj[key]=value; changed=True
                if changed:
                    c.execute(f'UPDATE {table} SET valores=?,actualizado=? WHERE jugadora_id=? AND fecha=?',
                              (json.dumps(obj,ensure_ascii=False),now,p,d))
                    result['complementadas']+=1
                else:result['sin_cambios']+=1
            else:
                c.execute(f'INSERT INTO {table} VALUES (?,?,?,?)',(p,d,json.dumps(incoming,ensure_ascii=False),now))
                result['nuevas']+=1
    return result

def save_simulation(result, player):
    now=datetime.now(timezone.utc).isoformat()
    with connect() as c:
        c.execute('''INSERT INTO simulaciones(jugadora_id,fecha,fecha_objetivo,
           bienestar_demo,fatiga_demo,version,creado) VALUES(?,?,?,?,?,?,?)''',
           (player,result['fecha_datos'],result['fecha_objetivo'],result['bienestar_demo'],
            result['fatiga_demo'],result['version'],now))

def load_simulations():
    with connect() as c:
        rows=c.execute('''SELECT jugadora_id,fecha,fecha_objetivo,bienestar_demo,fatiga_demo,version,creado
          FROM simulaciones ORDER BY id DESC LIMIT 1000''').fetchall()
    keys=['jugadora_id','Fecha de datos','Fecha objetivo','Bienestar DEMO','Fatiga DEMO','Versión','Creado']
    return [dict(zip(keys,row)) for row in rows]

def reset_demo():
    """Solo invocar en modo demo. Nunca en una instalación con datos reales."""
    with connect() as c:
        c.execute('DELETE FROM simulaciones')
        c.execute('DELETE FROM diario')
        c.execute('DELETE FROM evaluaciones')
        c.execute('DELETE FROM jugadoras')


def apply_source_updates(players, daily, periodic):
    """Aplica un lote validado en UNA transacción o lo revierte completo.

    Un dato ausente no borra el histórico. Un valor nuevo que contradice una
    medición existente se rechaza (la corrección exige revisión específica).
    """
    counters = {'jugadoras_nuevas': 0, 'filas_nuevas': 0,
                'filas_complementadas': 0, 'filas_sin_cambios': 0}
    now = datetime.now(timezone.utc).isoformat()
    with connect() as c:
        for p in players:
            old = c.execute('SELECT nombre FROM jugadoras WHERE jugadora_id=?',
                            (p['jugadora_id'],)).fetchone()
            if old is not None:
                if old[0] != p['nombre']:
                    raise ValueError(f"ID asignado a otro nombre: {p['jugadora_id']}")
                continue
            c.execute('INSERT INTO jugadoras VALUES (?,?,?)',
                      (p['jugadora_id'], p['nombre'], p.get('posicion')))
            counters['jugadoras_nuevas'] += 1
        for table, rows in (('diario', daily), ('evaluaciones', periodic)):
            for r in rows:
                pid, day = r['jugadora_id'], r['Fecha']
                if c.execute('SELECT 1 FROM jugadoras WHERE jugadora_id=?', (pid,)).fetchone() is None:
                    raise ValueError(f'Jugadora no registrada: {pid}')
                incoming = {k: v for k, v in r.items()
                            if k not in ('jugadora_id', 'Fecha') and v is not None}
                if not incoming:
                    continue
                old = c.execute(f'SELECT valores FROM {table} WHERE jugadora_id=? AND fecha=?',
                                (pid, day)).fetchone()
                if old is None:
                    c.execute(f'INSERT INTO {table} VALUES (?,?,?,?)',
                              (pid, day, json.dumps(incoming, ensure_ascii=False), now))
                    counters['filas_nuevas'] += 1
                    continue
                obj = json.loads(old[0])
                conflicts = [f for f, v in incoming.items()
                             if obj.get(f) is not None and obj[f] != v]
                if conflicts:
                    raise ValueError(f"Valor histórico incompatible para {pid}, {day}: " +
                                     ', '.join(conflicts[:3]))
                changed = {k: v for k, v in incoming.items() if obj.get(k) is None}
                if changed:
                    obj.update(changed)
                    c.execute(f'UPDATE {table} SET valores=?,actualizado=? WHERE jugadora_id=? AND fecha=?',
                              (json.dumps(obj, ensure_ascii=False), now, pid, day))
                    counters['filas_complementadas'] += 1
                else:
                    counters['filas_sin_cambios'] += 1
    return counters
