"""Lectura y validación de hojas Excel por fuentes; acepta formato anterior.

No guarda nada si hay errores. Concatena variables por clave (jugadora, fecha)
sin sustituir valores faltantes ni inventar mediciones.
"""
from __future__ import annotations
from io import BytesIO
import pandas as pd
from .schema import CATEGORIES
from .template_spec import (SHEETS, SOURCE_COLUMNS, SOURCE_FIELDS,
                            DAILY_SOURCE_SHEETS, PERIODIC_SOURCE_SHEETS,
                            PLAYER_COLUMNS, DAILY_COLUMNS, PERIODIC_COLUMNS)
from .validation import PLAYER_ID_PATTERN, validate_record


def _null(x):
    try:
        if pd.isna(x):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(x, str) and not x.strip():
        return None
    return x.strip() if isinstance(x, str) else x


def _sheet(xl, sheet, required):
    df = pd.read_excel(xl, sheet_name=sheet)
    df.columns = [str(k).strip() for k in df.columns]
    if len(df.columns) != len(set(df.columns)):
        raise ValueError(f'Encabezados repetidos en la hoja {sheet}.')
    missing = [h for h in required if h not in df.columns]
    if missing:
        raise ValueError(f'En {sheet} faltan columnas: {", ".join(missing[:6])}.')
    return df.dropna(how='all').reset_index(drop=True)


def read_template(filename, content, existing_players=None):
    if not filename.lower().endswith('.xlsx'):
        raise ValueError('El archivo debe tener extensión .xlsx.')
    if len(content) > 10 * 1024 * 1024:
        raise ValueError('Archivo de más de 10 MB; divida los registros.')
    try:
        xl = pd.ExcelFile(BytesIO(content), engine='openpyxl')
    except Exception as exc:
        raise ValueError('No se pudo abrir el archivo Excel.') from exc

    new_format = all(s in xl.sheet_names for s in SHEETS)
    legacy_format = all(s in xl.sheet_names for s in ('JUGADORAS', 'DIARIO', 'EVALUACIONES'))
    if not (new_format or legacy_format):
        missing = [s for s in SHEETS if s not in xl.sheet_names]
        raise ValueError('Faltan hojas del nuevo formato: ' + ', '.join(missing) +
                         '. También se admite el formato anterior (JUGADORAS, DIARIO, EVALUACIONES).')
    groups = (
        [(s, SOURCE_COLUMNS[s], SOURCE_FIELDS[s],
          'diario' if s in DAILY_SOURCE_SHEETS else 'evaluaciones') for s in SOURCE_FIELDS]
        if new_format else
        [('DIARIO', DAILY_COLUMNS, DAILY_COLUMNS[2:], 'diario'),
         ('EVALUACIONES', PERIODIC_COLUMNS, PERIODIC_COLUMNS[2:], 'evaluaciones')]
    )
    dfs = {'JUGADORAS': _sheet(xl, 'JUGADORAS', PLAYER_COLUMNS)}
    for s, required, _, _ in groups:
        dfs[s] = _sheet(xl, s, required)

    report = {'formato': 'Por fuentes' if new_format else 'Anterior',
              'filas': {}, 'validas': {}, 'errores': [], 'avisos': [],
              'duplicados': 0}
    players, seen = [], set()
    existing = {p['jugadora_id']: p['nombre'] for p in (existing_players or [])}
    for idx, row in dfs['JUGADORAS'].iterrows():
        r = {c: _null(row.get(c)) for c in PLAYER_COLUMNS}
        pid, nombre, posicion = r['ID_jugadora'], r['Nombre_jugadora'], r['Posición']
        label = f'JUGADORAS fila {idx + 2}'
        if not isinstance(pid, str) or not PLAYER_ID_PATTERN.fullmatch(pid):
            report['errores'].append(f'{label}: ID_jugadora inválido.'); continue
        if not isinstance(nombre, str) or not (2 <= len(nombre) <= 120):
            report['errores'].append(f'{label}: Nombre_jugadora obligatorio.'); continue
        if pid in seen:
            report['errores'].append(f'{label}: ID repetido en JUGADORAS.'); continue
        if posicion is not None and posicion not in CATEGORIES['Posición']:
            report['errores'].append(f'{label}: posición no permitida.'); continue
        if pid in existing and existing[pid] != nombre:
            report['errores'].append(f'{label}: ID asignado a otro nombre.'); continue
        seen.add(pid)
        players.append({'jugadora_id': pid, 'nombre': nombre, 'posicion': posicion})
    valid_ids = seen | set(existing)
    mapped = {'diario': {}, 'evaluaciones': {}}
    for s, _, fields, destination in groups:
        source_seen = set()
        for idx, row in dfs[s].iterrows():
            pid = _null(row.get('ID_jugadora'))
            label = f'{s} fila {idx + 2}'
            if pid not in valid_ids:
                report['errores'].append(f'{label}: ID no registrado en JUGADORAS ni en el historial.'); continue
            candidate = {'jugadora_id': pid, 'Fecha': _null(row.get('Fecha'))}
            candidate.update({f: _null(row.get(f)) for f in fields})
            cleaned, errors, warnings = validate_record(candidate, forbid_future=True)
            if errors:
                report['errores'].append(f'{label}: ' + '; '.join(errors[:3])); continue
            vals = {f: cleaned.get(f) for f in fields if cleaned.get(f) is not None}
            if not vals:
                report['avisos'].append(f'{label}: no contiene mediciones; fila omitida.'); continue
            key = (cleaned['jugadora_id'], cleaned['Fecha'])
            target = mapped[destination].setdefault(key, {'jugadora_id': key[0], 'Fecha': key[1]})
            conflicts = [f for f, v in vals.items() if f in target and target[f] != v]
            if conflicts:
                report['errores'].append(f'{label}: valores incompatibles para el mismo ID y fecha: {", ".join(conflicts[:3])}.')
                continue
            if key in source_seen:
                report['duplicados'] += 1
            source_seen.add(key)
            target.update(vals)
            if warnings:
                report['avisos'].append(f'{label}: ' + '; '.join(warnings[:3]))

    daily = list(mapped['diario'].values())
    periodic = list(mapped['evaluaciones'].values())
    report['filas'] = {s: len(df) for s, df in dfs.items()}
    report['validas'] = {'JUGADORAS': len(players), 'DIARIO': len(daily),
                         'EVALUACIONES': len(periodic)}
    report['errores_total'] = len(report['errores'])
    report['avisos_total'] = len(report['avisos'])
    return players, daily, periodic, report


def read_source_updates(files: dict, existing_players=None):
    """Lee plantillas por fuente con NOMBRE y FECHA; no pide ni genera IDs.

    Las jugadoras existentes se vinculan por nombre único normalizado.
    Para nombres nuevos, el propio nombre funciona temporalmente como clave
    interna del registro, sin crear una codificación externa. Antes de activar
    este flujo con datos reales debe revisarse la homonimia y privacidad.
    """
    from collections import defaultdict
    import unicodedata
    from .template_spec import UPDATE_SOURCES

    def normalize_name(value):
        if not isinstance(value, str):
            return None
        value = unicodedata.normalize('NFC', ' '.join(value.split()))
        return value if 2 <= len(value) <= 120 else None

    def key_name(value):
        return unicodedata.normalize('NFC', value).casefold()

    unknown = set(files) - set(UPDATE_SOURCES)
    if unknown:
        raise ValueError('Fuente no permitida: ' + ', '.join(sorted(unknown)))

    by_name = defaultdict(list)
    for player in existing_players or []:
        name = normalize_name(player.get('nombre'))
        if name:
            by_name[key_name(name)].append(player)

    incoming_players = {}
    name_to_key = {}
    results = {'diario': {}, 'evaluaciones': {}}
    report = {'formato': 'Actualizaciones por fuente y nombre',
              'fuentes_recibidas': list(files),
              'fuentes_sin_actualizar': [k for k in UPDATE_SOURCES if k not in files],
              'filas': {}, 'validas': {}, 'errores': [], 'avisos': [],
              'duplicados': 0}

    used_existing_keys = {p['jugadora_id'] for p in existing_players or []}
    for source, (filename, content) in files.items():
        spec = UPDATE_SOURCES[source]
        if not filename.lower().endswith('.xlsx'):
            report['errores'].append(f'{spec["label"]}: se requiere archivo .xlsx.'); continue
        if len(content) > 10 * 1024 * 1024:
            report['errores'].append(f'{spec["label"]}: archivo mayor de 10 MB.'); continue
        try:
            xl = pd.ExcelFile(BytesIO(content), engine='openpyxl')
        except Exception:
            report['errores'].append(f'{spec["label"]}: no se pudo abrir el Excel.'); continue
        sheet = spec['sheet']
        if sheet not in xl.sheet_names:
            report['errores'].append(f'{spec["label"]}: se esperaba la hoja {sheet}.')
            continue
        try:
            df = _sheet(xl, sheet, ['Fecha', 'Nombre_jugadora', *spec['fields']])
        except ValueError as exc:
            report['errores'].append(str(exc)); continue

        report['filas'][source] = len(df)
        seen = set()
        n_valid = 0
        for idx, row in df.iterrows():
            label = f'{spec["label"]}, fila {idx + 2}'
            name = normalize_name(_null(row.get('Nombre_jugadora')))
            if name is None:
                report['errores'].append(f'{label}: Nombre_jugadora obligatorio (2–120 caracteres).'); continue
            nkey = key_name(name)
            matches = by_name.get(nkey, [])
            if len(matches) > 1:
                report['errores'].append(f'{label}: nombre ambiguo; existen varias jugadoras registradas con ese nombre. Se debe resolver manualmente.'); continue
            if matches:
                player_key = matches[0]['jugadora_id']
            else:
                # No se inventan identificadores. El nombre es una referencia
                # PROVISIONAL hasta que exista un método de identificación.
                player_key = name_to_key.setdefault(nkey, name)
                if player_key in used_existing_keys:
                    report['errores'].append(f'{label}: el nombre coincide con una clave antigua de otra jugadora; revisar manualmente.'); continue
            raw = {'jugadora_id': player_key, 'Fecha': _null(row.get('Fecha'))}
            raw.update({f: _null(row.get(f)) for f in spec['fields']})
            clean, errors, warnings = validate_record(raw, require_player=False, forbid_future=True)
            if errors:
                report['errores'].append(f'{label}: ' + '; '.join(errors[:3])); continue
            observed = {f: clean.get(f) for f in spec['fields'] if clean.get(f) is not None}
            if not observed:
                report['avisos'].append(f'{label}: sin mediciones, fila ignorada.'); continue
            obskey = (player_key, clean['Fecha'])
            if obskey in seen:
                report['duplicados'] += 1
            seen.add(obskey)
            destination = results[spec['destination']]
            old = destination.get(obskey)
            if old is None:
                destination[obskey] = {'jugadora_id': player_key, 'Fecha': obskey[1], **observed}
            else:
                conflicts = [f for f, val in observed.items() if f in old and old[f] != val]
                if conflicts:
                    report['errores'].append(f'{label}: valores incompatibles para la misma jugadora y fecha: ' +
                                             ', '.join(conflicts[:3]) + '.')
                    continue
                old.update(observed)
            n_valid += 1
            if not matches and player_key not in incoming_players:
                incoming_players[player_key] = {'jugadora_id': player_key, 'nombre': name, 'posicion': None}
            if warnings:
                report['avisos'].append(f'{label}: ' + '; '.join(warnings[:3]))
        report['validas'][source] = n_valid

    report['errores_total'] = len(report['errores'])
    report['avisos_total'] = len(report['avisos'])
    return (list(incoming_players.values()), list(results['diario'].values()),
            list(results['evaluaciones'].values()), report)


def find_existing_conflicts(rows, current, source_label='fuente'):
    """Bloquea cambios a un valor ya medido; los huecos SÍ se complementan."""
    present = {(r['jugadora_id'], r['Fecha']): r for r in current}
    conflicts = []
    for row in rows:
        key = (row['jugadora_id'], row['Fecha'])
        old = present.get(key, {})
        for field, value in row.items():
            if field not in ('jugadora_id', 'Fecha') and value is not None and \
                    old.get(field) is not None and old[field] != value:
                conflicts.append(f'{source_label}: {key[0]} · {key[1]} · {field}: '
                                 f'guardado={old[field]!r}, nuevo={value!r}')
    return conflicts
