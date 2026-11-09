"""Dragonas IDV/USFQ | Excel -> historial -> variables -> simulador.
NO contiene modelos entrenados. Para uso local protegido; no publicar con datos reales.
"""
from __future__ import annotations
import hmac
import os
from datetime import date, timedelta
from pathlib import Path
import pandas as pd
import streamlit as st

from src.demo_data import make_demo_records
from src.feature_builder import snapshot
from src.mock_model import demo_predict
from src.storage import (initialize, load_players, get_rows, save_players,
                         save_rows, save_simulation,load_simulations,reset_demo)
from src.workbook_io import read_template

ROOT=Path(__file__).resolve().parent
TEMPLATE=ROOT/'Plantilla_Carga_Dragonas.xlsx'
st.set_page_config(page_title='Dragonas | Wellness y fatiga',page_icon='🐉',layout='wide')
st.markdown('''<style>
.block-container{max-width:1290px;padding-top:1.3rem}
[data-testid="stMetric"]{border:1px solid #e6d8e5;background:#fbf7fb;padding:15px;border-radius:12px}
h1,h2,h3{letter-spacing:-.02em}
</style>''',unsafe_allow_html=True)

# Sin contraseña la aplicación funciona exclusivamente con registros ficticios.
# Repositorio de demostración pública: no activar modo privado mediante variables.
PASSWORD=''
PRIVATE=False
if PRIVATE and not st.session_state.get('auth_ok'):
    st.title('Acceso restringido · Dragonas IDV/USFQ')
    st.warning('Esta autenticación es solo para pruebas LOCALES. No sustituye identidad institucional ni cifrado.')
    with st.form('login'):
        supplied=st.text_input('Contraseña de acceso local',type='password')
        submitted=st.form_submit_button('Ingresar')
    if submitted:
        if hmac.compare_digest(PASSWORD,supplied):
            st.session_state['auth_ok']=True;st.rerun()
        st.error('Contraseña incorrecta.')
    st.stop()

initialize()
with st.sidebar:
    st.title('🐉 Dragonas IDV/USFQ')
    st.caption('Registro por Excel · Prototipo académico')
    if PRIVATE:
        st.success('Modo local restringido')
        if st.button('Cerrar sesión'):
            st.session_state['auth_ok']=False;st.rerun()
    else:
        st.info('Modo público DEMO. No subir datos reales.')
    view=st.radio('Menú',['Resumen','Plantilla Excel','Importar registros','Historial por jugadora',
                           'Control de faltantes','Simulador t→t+1','Historial de simulaciones','Ayuda'])
    st.divider()
    st.caption('⚠️ Simulaciones no validadas. No usar para decisiones médico-deportivas.')

st.title(view)
if PRIVATE:
    st.warning('USO LOCAL DE PRUEBA: el Excel contiene nombres y registros sensibles. No desplegar esta versión con datos reales en un hosting público.')
else:
    st.warning('DEMO PÚBLICA: solo datos ficticios. Está bloqueada la carga de datos de jugadoras reales.')

players=load_players();daily=get_rows('diario');periodic=get_rows('evaluaciones')
name_by_id={p['jugadora_id']:p['nombre'] for p in players}

def pretty(row):
    return name_by_id.get(row,row)+' ('+row+')'

def with_names(rows):
    out=[]
    for r in rows:
        obj=dict(r)
        obj['Jugadora']=name_by_id.get(obj.get('jugadora_id'),'ID no encontrado')
        out.append(obj)
    return out

def demo_seed():
    records=make_demo_records()
    ids=sorted(set(r['jugadora_id'] for r in records))
    save_players([{'jugadora_id':p,'nombre':f'Jugadora ficticia {p[-2:]}','posicion':None} for p in ids])
    save_rows('diario',records)
    measures=[]
    for p in ids:
        measures.append({'jugadora_id':p,'Fecha':'2026-09-08',
                         'CMJ Altura de Salto por Impulso Momento (cm)':32.2,
                         'Nordic Fuerza Promedio Izquierda (N)':290.0,
                         'Nordic Fuerza Promedio Derecha (N)':300.0})
        measures.append({'jugadora_id':p,'Fecha':'2026-09-22',
                         'Hemoglobina (g/dL)':13.2,'Ferritina':32.0})
    save_rows('evaluaciones',measures)

if view=='Resumen':
    if not players:
        st.info('Todavía no existen jugadoras registradas en esta instalación.')
        if not PRIVATE and st.button('Cargar datos sintéticos para explorar',type='primary'):
            demo_seed();st.rerun()
    else:
        a,b,c,d=st.columns(4)
        a.metric('Jugadoras',len(players))
        b.metric('Registros diarios',len(daily))
        c.metric('Fechas de evaluación',len(periodic))
        d.metric('Días con Wellness',sum(bool(r.get('Tipo de fatiga')) for r in daily))
        st.subheader('Disponibilidad de información')
        cov=pd.DataFrame([
           {'Medición':'Wellness','Registros':sum(r.get('Tipo de fatiga') is not None for r in daily)},
           {'Medición':'RPE','Registros':sum(r.get('RPE_diario') is not None for r in daily)},
           {'Medición':'GPS','Registros':sum(r.get('Distancia total (m)') is not None for r in daily)},
           {'Medición':'CMJ','Registros':sum(r.get('CMJ Altura de Salto por Impulso Momento (cm)') is not None for r in periodic)},
           {'Medición':'Hemoglobina','Registros':sum(r.get('Hemoglobina (g/dL)') is not None for r in periodic)},
        ]).set_index('Medición')
        st.bar_chart(cov)
        st.subheader('Últimos registros diarios')
        show=pd.DataFrame(with_names(daily[-30:]))
        selected=['Jugadora','Fecha','Tipo de fatiga','Estado de sueño','RPE_diario','Load_total','Distancia total (m)']
        st.dataframe(show.reindex(columns=selected),hide_index=True,use_container_width=True)
        st.caption('Estos indicadores describen registros disponibles; no son predicciones.')

elif view=='Plantilla Excel':
    st.write('La médica trabaja en Excel y solo sube el archivo completado a la aplicación privada.')
    st.download_button('⬇️ Descargar plantilla de Excel',data=TEMPLATE.read_bytes(),
                       file_name='Plantilla_Carga_Dragonas.xlsx',
                       mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',type='primary')
    st.markdown('''**JUGADORAS:** ID, nombre y posición.  
**DIARIO:** una fila por jugadora y fecha; Wellness, cargas y GPS cuando existan.  
**EVALUACIONES:** mediciones clínicas y neuromusculares, registradas solo cuando se realicen.  
**Regla:** celdas vacías = no medido; no introducir 0 ni copiar valores anteriores.''')
    st.info('No se necesita volver a subir todo el historial en cada carga: la base conserva registros anteriores.')

elif view=='Importar registros':
    if not PRIVATE:
        st.error('Importación deshabilitada en la versión pública. Los nombres y registros solo se pueden cargar en la instalación local autorizada.')
        st.info('Para revisar el flujo sin datos reales utiliza el botón de datos sintéticos en Resumen.')
    else:
        upload=st.file_uploader('Adjunta el Excel completado usando la plantilla',type=['xlsx'])
        if upload:
            try:
                ps,ds,es,report=read_template(upload.name,upload.getvalue(),players)
                c1,c2,c3=st.columns(3)
                c1.metric('Jugadoras válidas',report['validas']['JUGADORAS'])
                c2.metric('Registros diarios válidos',report['validas']['DIARIO'])
                c3.metric('Evaluaciones válidas',report['validas']['EVALUACIONES'])
                if report['avisos']:
                    with st.expander(f'Avisos ({report["avisos_total"]})'):
                        st.write(report['avisos'][:100])
                if report['errores']:
                    st.error(f'Se encontraron {report["errores_total"]} errores. Corrige el Excel antes de importar: no se guardó nada.')
                    st.write(report['errores'][:100])
                else:
                    st.success('Estructura válida. Los vacíos no borrarán mediciones previamente guardadas.')
                    overwrite=st.checkbox('Sobrescribir campos existentes que tengan un valor diferente (solo correcciones verificadas)')
                    with st.form('confirm_upload'):
                        confirm=st.checkbox('Confirmo que tengo autorización para tratar los datos y que el dispositivo es privado')
                        submitted=st.form_submit_button('Guardar registros validados',type='primary')
                    if submitted:
                        if not confirm:st.error('Se requiere confirmación antes de guardar.')
                        else:
                            a=save_players(ps)
                            b=save_rows('diario',ds,overwrite_conflicts=overwrite)
                            c=save_rows('evaluaciones',es,overwrite_conflicts=overwrite)
                            st.success(f'Jugadoras nuevas: {a["nuevas"]}; diarios nuevos: {b["nuevas"]}; evaluaciones nuevas: {c["nuevas"]}.')
                            if b['campos_conflictivos']+c['campos_conflictivos']:
                                st.warning('Se identificaron valores conflictivos. '+
                                           ('Se aplicaron correcciones solicitadas.' if overwrite else 'Se conservaron los valores originales.'))
                            st.rerun()
            except ValueError as exc:
                st.error(str(exc))

elif view in ('Historial por jugadora','Control de faltantes','Simulador t→t+1'):
    if not players:
        st.info('Primero importa registros o carga la demostración.')
    else:
        ids=sorted(name_by_id,key=lambda pid:name_by_id[pid])
        person=st.selectbox('Seleccionar jugadora',ids,format_func=pretty)
        days=sorted({r['Fecha'] for r in daily if r['jugadora_id']==person},reverse=True)
        if view=='Historial por jugadora':
            st.subheader('Registros diarios')
            st.dataframe(pd.DataFrame([r for r in daily if r['jugadora_id']==person]).drop(columns=['jugadora_id'],errors='ignore'),
                         hide_index=True,use_container_width=True)
            st.subheader('Evaluaciones periódicas')
            per=pd.DataFrame([r for r in periodic if r['jugadora_id']==person])
            if len(per):st.dataframe(per.drop(columns=['jugadora_id'],errors='ignore'),hide_index=True,use_container_width=True)
            else:st.info('Sin evaluaciones periódicas cargadas.')
        elif not days:
            st.warning('Esta jugadora todavía no tiene registros diarios.')
        else:
            day=st.selectbox('Fecha de referencia (día t)',days)
            with st.expander('Reglas preliminares de antigüedad',expanded=False):
                st.caption('Estos límites son ejemplos para probar la herramienta; se revisarán al entrenar los modelos.')
                max_clinical=st.number_input('Vigencia clínica DEMO (días)',min_value=1,max_value=365,value=90)
                max_neuro=st.number_input('Vigencia neuromuscular DEMO (días)',min_value=1,max_value=365,value=60)
            snap=snapshot(person,day,daily,periodic,clinical_max_days=max_clinical,neuro_max_days=max_neuro)
            if view=='Control de faltantes':
                st.caption('No se introduce el último valor observado como una medición nueva: se conserva la fecha de origen.')
                audit=pd.DataFrame(snap['auditoria'])
                states=audit['Procedencia'].value_counts().rename_axis('Estado').reset_index(name='Variables')
                st.dataframe(states,hide_index=True,use_container_width=True)
                st.dataframe(audit,hide_index=True,use_container_width=True)
                st.subheader('Ventanas de carga histórica (solo observaciones hasta t)')
                st.json(snap['ventanas'])
                st.info('No rellenar Wellness, RPE o GPS ausentes con el último día automáticamente: depende del tratamiento validado durante entrenamiento.')
            else:
                st.subheader('Predicción del día siguiente: DEMOSTRACIÓN NO VALIDADA')
                today=dict(jugadora_id=person,Fecha=day,**snap['valores'])
                try:
                    result=demo_predict(today,daily)
                except ValueError as e:
                    st.error('No es posible simular: '+str(e))
                else:
                    a,b,c=st.columns(3)
                    a.metric('Bienestar ficticio (0–100)',result['bienestar_demo'])
                    b.metric('Fatiga ficticia',result['fatiga_demo'])
                    c.metric('Fecha objetivo (t+1)',result['fecha_objetivo'])
                    st.error('⚠️ Fórmula artificial sin entrenamiento ni validación; no es una recomendación médica.')
                    st.caption('Las evaluaciones periódicas se resuelven en el procesador de entradas; la fórmula DEMO aún no las usa. El modelo real determinará cuáles son sus predictores.')
                    with st.expander('Auditoría de las variables utilizadas y su origen'):
                        st.dataframe(pd.DataFrame(snap['auditoria']),hide_index=True,use_container_width=True)
                        st.json(snap['ventanas'])
                    if st.button('Guardar resultado etiquetado SIMULACIÓN'):
                        save_simulation(result,person);st.success('Resultado de demostración guardado.')

elif view=='Historial de simulaciones':
    sim=load_simulations()
    if sim:
        st.dataframe(pd.DataFrame(with_names(sim)),hide_index=True,use_container_width=True)
    else:st.info('Aún no existen simulaciones guardadas.')

elif view=='Ayuda':
    st.markdown('''### Guía de trabajo
1. Descarga la plantilla desde **Plantilla Excel**.
2. Registra las jugadoras (ID único y nombre visible para la médica).
3. Cada día, agrega las filas correspondientes en **DIARIO**; solo al medirse, añade **EVALUACIONES**.
4. Importa el archivo en la instalación local protegida. Los datos vacíos no se sustituyen por 0.
5. Consulta el **Control de faltantes** antes de ejecutar el simulador de prueba.

### Políticas de datos faltantes
- Una evaluación periódica puede recuperarse de la última fecha **anterior o igual** a t.
- La fecha original y el número de días transcurridos se muestran para auditoría.
- Hay límites de antigüedad configurables **solo demostrativos**. No son reglas clínicas y deben acordarse al entrenar los modelos.
- Las mediciones diarias faltantes se mantienen como faltantes; se necesita la regla entrenada.
- No se consulta ningún dato posterior a t para predecir t+1.

### Seguridad y límites
Esta versión guarda nombres y nuevos registros en SQLite local **sin cifrado en reposo**.
Úsala exclusivamente en un dispositivo autorizado, con contraseña local, nunca como un sitio público que trate datos reales. Para desplegarla en nube se necesitarán login individual, autorización, una base persistente protegida, auditoría y respaldo. Streamlit Community Cloud no ofrece persistencia fiable mediante SQLite local. **Los modelos reales todavía no están entrenados.**

### Módulo futuro de ML
El procesador `snapshot` construye un conjunto de entradas con fechas de origen y ventanas 3/7/14/28. Una vez que los modelos estén entrenados, reemplazar las reglas de demostración por el pipeline final de imputación, normalización y predicción, comprobando su igualdad con el notebook.
    ''')
    if not PRIVATE:
        st.divider()
        st.caption('En modo público únicamente puedes restablecer registros DEMO.')
        if st.button('Eliminar todos los datos ficticios de esta instancia'):
            reset_demo();st.rerun()
