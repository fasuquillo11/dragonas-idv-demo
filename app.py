"""Dragonas IDV/USFQ: dashboard + simulador + registro.

Solo demostración con datos sintéticos. NO es un modelo ML entrenado ni validado.
Nunca cargar información identificable en esta instancia pública.
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd
import streamlit as st

from src.demo_data import make_demo_records
from src.export_results import export_csv, result_to_row
from src.feature_builder import snapshot
from src.mock_model import demo_predict
from src.storage import (initialize, load_players, get_rows, save_players,
                         save_rows, save_simulation, load_simulations, apply_source_updates)
from src.template_spec import SOURCE_FIELDS, UPDATE_SOURCES
from src.workbook_io import read_source_updates, find_existing_conflicts

ROOT = Path(__file__).resolve().parent
TEMPLATE_DIR = ROOT / 'plantillas'
PRIVATE = False  # Versión pública: nunca habilitar carga de información real.

st.set_page_config(page_title='Dragonas IDV/USFQ | Panel de rendimiento', page_icon='🐉', layout='wide')
st.markdown('''
<style>
:root{--navy:#15243e;--magenta:#bd2d71;--muted:#657188}
.block-container{max-width:1330px;padding-top:1.45rem;padding-bottom:3rem}
[data-testid="stAppViewContainer"]{background:#f8f9fc}
[data-testid="stSidebar"]{background:#15243e}
[data-testid="stSidebar"] *{color:#f5f7fc!important}
[data-testid="stMetric"]{background:#fff;padding:18px 20px;border:1px solid #e7eaf0;border-radius:15px;box-shadow:0 2px 10px rgba(21,36,62,.025)}
[data-testid="stMetricLabel"]{color:#64748b}
[data-testid="stMetricValue"]{color:#17243e}
h1,h2,h3{letter-spacing:-.025em;color:#15243e}
h1{font-weight:780!important}
div.stButton>button[kind="primary"],div.stDownloadButton>button[kind="primary"]{background:#bd2d71;border-color:#bd2d71;color:white;border-radius:10px}
div.stButton>button,div.stDownloadButton>button{border-radius:10px}
.hero{padding:26px 30px;border-radius:18px;background:linear-gradient(115deg,#15243e,#283a5f);color:white;margin-bottom:18px}
.hero .overline{font-size:12px;color:#efbfd7;font-weight:700;letter-spacing:.09em;text-transform:uppercase}
.hero h2{color:white!important;font-size:27px;margin:7px 0 11px}
.hero p{font-size:15px;color:#e1e8f2;margin:0;max-width:820px;line-height:1.6}
.section-label{font-weight:750;color:#263852;font-size:17px;margin:16px 0 8px}
.soft-note{background:#fff3f8;color:#772249;border:1px solid #f0d5e2;padding:11px 15px;border-radius:11px;font-size:13px;margin:12px 0}
.small-muted{color:#6e7890;font-size:13px}
hr{border-color:#e9ecf2}
</style>
''', unsafe_allow_html=True)

initialize()
players = load_players()
daily = get_rows('diario')
periodic = get_rows('evaluaciones')
sims = load_simulations()
name_by_id = {p['jugadora_id']: p['nombre'] for p in players}


def player_label(pid):
    return name_by_id.get(pid, 'Jugadora ficticia')


def seed_demo():
    records = make_demo_records()
    ids = sorted({r['jugadora_id'] for r in records})
    save_players([{'jugadora_id': p, 'nombre': f'Jugadora ficticia {p[-2:]}', 'posicion': None} for p in ids])
    save_rows('diario', records)
    measures = []
    for p in ids:
        measures.extend([
            {'jugadora_id': p, 'Fecha': '2026-09-08',
             'CMJ Altura de Salto por Impulso Momento (cm)': 32.2,
             'Nordic Fuerza Promedio Izquierda (N)': 290.0,
             'Nordic Fuerza Promedio Derecha (N)': 300.0},
            {'jugadora_id': p, 'Fecha': '2026-09-22',
             'Hemoglobina (g/dL)': 13.2, 'Ferritina': 32.0},
        ])
    save_rows('evaluaciones', measures)


def saved_simulation_rows():
    rows = []
    for record in sims:
        obj = dict(record)
        obj['Jugadora'] = name_by_id.get(obj['jugadora_id'], 'Nombre no disponible')
        rows.append(obj)
    return rows


with st.sidebar:
    st.markdown('## 🐉 DRAGONAS')
    st.caption('IDV / USFQ  ·  Performance Analytics')
    st.divider()
    st.markdown('**Prototipo académico**')
    st.caption('Predicción de bienestar y clasificación anticipada de fatiga para el día siguiente.')
    st.info('Versión DEMO: datos ficticios y reglas simuladas. Sin modelos entrenados.')
    st.divider()
    st.caption('Las decisiones deportivas y clínicas requieren evaluación profesional.')

head_l, head_r = st.columns([4, 1])
with head_l:
    st.markdown('### Plataforma de monitoreo del bienestar y la fatiga')
with head_r:
    st.caption('● DEMOSTRACIÓN PÚBLICA')
view = st.radio('Navegación principal',
                ['Inicio · Dashboard', 'Simulador', 'Registro de simulaciones'],
                horizontal=True, label_visibility='collapsed')
st.divider()

if view == 'Inicio · Dashboard':
    st.markdown('''<div class="hero"><div class="overline">Dragonas IDV/USFQ · Proyecto de investigación</div>
    <h2>Del registro diario a una visión del día siguiente</h2>
    <p>Esta herramienta busca apoyar el monitoreo de las jugadoras mediante la predicción del bienestar y la
    clasificación anticipada de la fatiga a partir de mediciones actuales e históricas. En esta versión,
    los resultados de predicción son simulaciones ficticias, no salidas de modelos entrenados.</p></div>''',
    unsafe_allow_html=True)
    if not players:
        st.info('La demostración aún no tiene registros sintéticos. Carga los datos de ejemplo para explorar el dashboard.')
        if st.button('Cargar datos ficticios de demostración', type='primary'):
            seed_demo()
            st.rerun()
    else:
        observed_dates = sorted({r['Fecha'] for r in daily}, reverse=True)
        a, b = st.columns([3, 1])
        with a:
            st.markdown('#### Dashboard de cobertura del equipo')
            st.caption('Muestra disponibilidad de información, no estimaciones clínicas ni disponibilidad competitiva.')
        with b:
            day = st.selectbox('Fecha de referencia', observed_dates)
        st.caption(f'{len(players)} jugadoras registradas. Cada fuente se presenta según la información disponible a la fecha elegida.')
        st.markdown('#### Disponibilidad por fuente')
        left, right = st.columns([1.05, 1], gap='large')
        source_rows = []
        table_rows = []
        source_counts = {key: 0 for key in UPDATE_SOURCES}
        for p in players:
            snap = snapshot(p['jugadora_id'], day, daily, periodic)
            values = snap['valores']
            state = {key: any(values.get(f) is not None for f in spec['fields'])
                     for key, spec in UPDATE_SOURCES.items()}
            for key in source_counts:
                source_counts[key] += int(state[key])
            table_rows.append({'Jugadora': p['nombre'],
                               **{spec['label']: 'Sí' if state[key] else 'Sin dato disponible'
                                  for key, spec in UPDATE_SOURCES.items()}})
        summary = st.columns(4)
        for idx, (key, spec) in enumerate(UPDATE_SOURCES.items()):
            summary[idx].metric(spec['label'], f'{source_counts[key]} / {len(players)}')
            source_rows.append({'Fuente': spec['label'], 'Jugadoras con información': source_counts[key]})
        st.caption('GPS y Wellness y Carga: registros del día. Biomecánicos y Laboratorio: última medición previa vigente según reglas DEMO.')
        with left:
            st.markdown('**Jugadoras con información disponible**')
            st.bar_chart(pd.DataFrame(source_rows).set_index('Fuente'), height=270)
        with right:
            st.markdown('**Vista rápida por jugadora**')
            st.dataframe(pd.DataFrame(table_rows), hide_index=True, use_container_width=True, height=300)
        st.caption('Laboratorio y Biomecánicos usan mediciones previas dentro de una vigencia provisional de 90 y 60 días respectivamente. Estos límites aún deben validarse.')

        st.markdown('#### Resultados guardados de demostración')
        if sims:
            charts_left, charts_right = st.columns(2, gap='large')
            data = pd.DataFrame(saved_simulation_rows())
            with charts_left:
                st.markdown('**Clasificación de fatiga simulada**')
                counts = data['Fatiga DEMO'].value_counts().reindex(['BAJA', 'MODERADA', 'ALTA'], fill_value=0)
                st.bar_chart(counts.rename('Simulaciones'), height=230)
            with charts_right:
                st.markdown('**Últimos resultados**')
                st.dataframe(data[['Jugadora', 'Fecha objetivo', 'Bienestar DEMO', 'Fatiga DEMO']].head(8),
                             hide_index=True, use_container_width=True, height=245)
            st.caption('Los resultados son ficticios, dependen de reglas arbitrarias y no deben utilizarse para tomar decisiones.')
        else:
            st.info('Aún no se han guardado simulaciones. Entra a «Simulador» para generar un resultado de ejemplo.')

elif view == 'Simulador':
    st.title('Simulador de bienestar y fatiga')
    st.caption('Flujo propuesto: preparar el Excel por fuente → cargar información en la futura versión privada → seleccionar jugadora y fecha → simular → descargar resultado.')
    with st.container(border=True):
        st.markdown('#### 1. Actualizar datos por fuente')
        st.write('Descarga **solo la plantilla de la fuente** que tenga nuevos registros. No es necesario volver a subir las demás.')
        st.caption('Cada archivo tiene una única hoja de captura con los encabezados correspondientes. El sistema relaciona los datos por Nombre_jugadora y Fecha, de manera provisional.')
        uploads = {}
        for key, spec in UPDATE_SOURCES.items():
            with st.container(border=True):
                info, download, upload = st.columns([1.55, 1.15, 2.1], gap='medium', vertical_alignment='center')
                with info:
                    st.markdown(f'**{spec["label"]}**')
                    st.caption(spec['description'])
                with download:
                    filename = spec['filename']
                    st.download_button('⬇ Descargar plantilla', data=(TEMPLATE_DIR / filename).read_bytes(),
                                       file_name=filename,
                                       mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                                       key=f'descargar_{key}', use_container_width=True)
                with upload:
                    attached = st.file_uploader(f'Archivo actualizado: {spec["label"]}',
                                                type=['xlsx'], key=f'actualizar_{key}',
                                                disabled=not PRIVATE,
                                                help='Si no cargas ningún archivo, esta fuente se conserva sin modificaciones.')
                    if attached is None:
                        st.caption('Sin archivo nuevo · sin cambios en esta fuente.')
                    else:
                        uploads[key] = (attached.name, attached.getvalue())
                        st.caption('Archivo seleccionado · pendiente de validación y guardado.')
        st.info('**Regla de actualización:** una plantilla no subida significa que no hay datos nuevos para esa fuente. El historial se mantiene; las celdas vacías no borran datos anteriores.')
        st.caption('Por ahora el nombre identifica provisionalmente cada jugadora. Nombres iguales o inconsistentes requieren revisión manual; los ID se definirán más adelante.')
        with st.expander('Instrucciones para copiar y pegar datos'):
            st.markdown('''1. Descarga la plantilla de la fuente que vas a actualizar.
2. Copia las filas desde el registro original debajo de los encabezados. Completa **Fecha** y **Nombre_jugadora** en cada fila.
3. Escribe el mismo nombre en todas las fuentes, con una ortografía consistente. Por ahora no se necesita un ID.
4. Deja en blanco los valores que no se midieron. No conviertas ausencias en ceros ni repitas mediciones previas.
5. En la futura versión privada, sube únicamente las plantillas nuevas y confirma la actualización.

Una jugadora puede aparecer en GPS y en Wellness y Carga en la misma fecha: las variables se complementan, no se crean dos registros diarios. Los registros de Biomecánicos y Laboratorio conservan su **fecha real de medición**.''')
        if not PRIVATE:
            st.warning('**Demostración pública:** puedes descargar las cuatro plantillas, pero la carga de archivos está bloqueada para evitar exponer información de jugadoras. El ingreso real requiere una versión privada con autenticación y base de datos segura.')
        elif uploads:
            if st.button('Validar y guardar fuentes seleccionadas', type='primary', use_container_width=True):
                new_players, new_daily, new_periodic, report = read_source_updates(uploads, players)
                conflicts = (find_existing_conflicts(new_daily, daily, 'Registros diarios') +
                             find_existing_conflicts(new_periodic, periodic, 'Evaluaciones'))
                errors = report['errores'] + conflicts
                if errors:
                    st.error(f'No se guardó ninguna fuente. Se encontraron {len(errors)} incompatibilidades:')
                    st.write(errors[:30])
                    if len(errors) > 30:
                        st.caption(f'Hay {len(errors) - 30} errores adicionales.')
                else:
                    try:
                        summary = apply_source_updates(new_players, new_daily, new_periodic)
                    except ValueError as exc:
                        st.error(f'No se guardó el lote: {exc}')
                    else:
                        st.success(f'Actualización completada: {len(uploads)} fuente(s) recibida(s); '
                                   f'{summary["filas_nuevas"]} registros nuevos; '
                                   f'{summary["filas_complementadas"]} complementados; '
                                   f'{summary["filas_sin_cambios"]} sin cambios. '
                                   'Las fuentes no subidas no se modificaron.')
                        st.session_state.pop('active_result', None)
                        st.info('Los cambios aparecerán en el dashboard y el simulador al recargar la página.')
                    if report['avisos']:
                        st.caption(f'{len(report["avisos"])} avisos: {"; ".join(report["avisos"][:3])}')
        else:
            st.caption('No hay archivos seleccionados. No se realizará ninguna actualización.')
    st.markdown('#### 2. Ejecutar simulación')
    if not players:
        st.info('Primero carga los registros ficticios desde la sección Inicio.')
    else:
        ids = sorted(name_by_id, key=lambda p: name_by_id[p])
        c1, c2 = st.columns(2)
        with c1:
            person = st.selectbox('Jugadora', ids, format_func=player_label, key='sim_player')
        dates = sorted({r['Fecha'] for r in daily if r['jugadora_id'] == person}, reverse=True)
        if not dates:
            st.warning('No hay registros diarios de esta jugadora.')
        else:
            with c2:
                day = st.selectbox('Fecha de referencia (t)', dates, key='sim_date')
            snap = snapshot(person, day, daily, periodic)
            daily_fields = SOURCE_FIELDS['WELLNESS'] + SOURCE_FIELDS['ENTRENAMIENTO'] + SOURCE_FIELDS['GPS']
            filled = sum(snap['valores'].get(f) is not None for f in daily_fields)
            summary_cols = st.columns(3)
            summary_cols[0].metric('Variables diarias disponibles', f'{filled}/{len(daily_fields)}')
            summary_cols[1].metric('Mediciones periódicas disponibles',
                                   sum(snap['valores'].get(f) is not None for f in
                                       SOURCE_FIELDS['CLINICA'] + SOURCE_FIELDS['NEUROMUSCULAR']))
            summary_cols[2].metric('Datos de carga en 28 días',
                                   f'{snap["ventanas"]["dias_con_carga_28d"]} días')
            with st.expander('Revisar datos de origen, faltantes y ventanas temporales'):
                st.dataframe(pd.DataFrame(snap['auditoria']), hide_index=True, use_container_width=True)
                st.dataframe(pd.DataFrame([
                    {'Ventana': f'{n} días',
                     'Carga observada': snap['ventanas'][f'carga_observada_{n}d'],
                     'Días con carga': snap['ventanas'][f'dias_con_carga_{n}d'],
                     'Cobertura (%)': snap['ventanas'][f'cobertura_{n}d']}
                    for n in (3, 7, 14, 28)]), hide_index=True, use_container_width=True)
                st.caption('No se utilizan datos posteriores a la fecha de referencia; ninguna ausencia se convierte automáticamente en cero.')
            if st.button('Ejecutar simulación t → t+1', type='primary', use_container_width=True):
                today = {'jugadora_id': person, 'Fecha': day, **snap['valores']}
                try:
                    result = demo_predict(today, daily)
                except ValueError as exc:
                    st.session_state.pop('active_result', None)
                    st.error(f'No es posible simular: {exc}')
                else:
                    st.session_state['active_result'] = {'player': person, 'day': day, 'result': result}
            active = st.session_state.get('active_result')
            if active and active['player'] == person and active['day'] == day:
                result = active['result']
                st.markdown('#### 3. Resultado de demostración')
                x, y, z = st.columns(3)
                x.metric('Bienestar ficticio (0–100)', result['bienestar_demo'])
                y.metric('Fatiga ficticia', result['fatiga_demo'])
                z.metric('Fecha objetivo (t+1)', result['fecha_objetivo'])
                st.markdown('<div class="soft-note">⚠️ Resultado artificial, sin entrenamiento ni validación. No representa una estimación médica ni una recomendación de participación deportiva.</div>', unsafe_allow_html=True)
                st.caption('Las mediciones históricas se preparan para el futuro modelo, pero la fórmula de simulación actual no las utiliza todas.')
                actions = st.columns(2)
                with actions[0]:
                    if st.button('Guardar en registro', use_container_width=True):
                        save_simulation(result, person)
                        st.success('Simulación guardada en el registro de esta demostración.')
                with actions[1]:
                    row = result_to_row(result, person, name_by_id[person])
                    st.download_button('⬇ Descargar resultado (Excel/CSV)',
                                       data=export_csv([row]),
                                       file_name=f'simulacion_dragonas_{day}.csv',
                                       mime='text/csv', use_container_width=True)
                with st.expander('Ver contribuciones de la fórmula de ejemplo'):
                    st.dataframe(pd.DataFrame([
                        {'Variable': k, 'Contribución ficticia': v}
                        for k, v in result['detalle_arbitrario'].items()]),
                        hide_index=True, use_container_width=True)
            else:
                st.caption('Selecciona la jugadora y fecha; después ejecuta la simulación para habilitar la descarga del resultado.')

elif view == 'Registro de simulaciones':
    st.title('Registro de simulaciones')
    st.caption('Historial de resultados ficticios guardados. No es un registro de predicciones validadas.')
    if not sims:
        st.info('Aún no hay simulaciones guardadas. Ejecuta y guarda una desde «Simulador».')
    else:
        all_rows = saved_simulation_rows()
        names = sorted({r['Jugadora'] for r in all_rows})
        filter_a, filter_b = st.columns(2)
        with filter_a:
            selected = st.selectbox('Filtrar por jugadora', ['Todas', *names])
        with filter_b:
            fatigue = st.selectbox('Filtrar por fatiga', ['Todas', 'BAJA', 'MODERADA', 'ALTA'])
        filtered = [r for r in all_rows if
                    (selected == 'Todas' or r['Jugadora'] == selected) and
                    (fatigue == 'Todas' or r['Fatiga DEMO'] == fatigue)]
        st.metric('Simulaciones encontradas', len(filtered))
        columns = ['Jugadora', 'Fecha de datos', 'Fecha objetivo',
                   'Bienestar DEMO', 'Fatiga DEMO', 'Versión']
        st.dataframe(pd.DataFrame(filtered).reindex(columns=columns),
                     hide_index=True, use_container_width=True)
        st.download_button('⬇ Descargar registro filtrado (Excel/CSV)',
                           data=export_csv(filtered), file_name='registro_simulaciones_dragonas.csv',
                           mime='text/csv', type='primary')
        st.caption('Los registros de esta demo pueden perderse cuando el servidor gratuito se reinicia; no es almacenamiento permanente.')

st.divider()
st.caption('Dragonas IDV/USFQ · Prototipo académico · Datos sintéticos · Simulador no entrenado · 2026')
