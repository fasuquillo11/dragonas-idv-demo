"""DRAGONAS | Panel de proyección de la próxima sesión.

Interfaz con apariencia de producto final, alimentada exclusivamente por
información SINTÉTICA. No utiliza datos ni nombres reales del equipo.
La regresión de bienestar se estimó sobre etiquetas sintéticas: NO VALIDADA.
"""
from __future__ import annotations
from datetime import date,timedelta
from io import BytesIO
from pathlib import Path
from hashlib import sha256
import pandas as pd
import streamlit as st

from src.forecast import (
    COL, CAT_CODES, NUMERIC, DAILY_COLUMNS, OLS_INTERCEPT,
    OLS_COEFFICIENTS, roster, compute_forecast, forecast_latest,
)

BASE=Path(__file__).resolve().parent
ASSETS=BASE/'data'
TEMPLATES=BASE/'plantillas'
st.set_page_config(
    page_title='Dragonas | Panel de rendimiento',
    page_icon='🐉',layout='wide',initial_sidebar_state='collapsed')

st.markdown('''
<style>
:root{--navy:#15243e;--magenta:#c13578;--muted:#69758c;--line:#e9edf4}
.stApp{background:#f7f8fc;color:#1e2a40}
.block-container{max-width:1450px;padding-top:1.25rem;padding-bottom:3.6rem}
[data-testid="stMetric"]{background:white;border:1px solid #e6eaf2;border-radius:16px;padding:16px 18px;box-shadow:0 4px 16px rgba(15,33,59,.025)}
[data-testid="stMetricLabel"]{color:#5f7089;font-size:14px}
[data-testid="stMetricValue"]{color:#182943;font-weight:730}
[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"]){border-radius:17px}
div.stButton>button[kind="primary"],div.stDownloadButton>button[kind="primary"]{border-radius:11px;background:#c13578;border-color:#c13578;color:white;font-weight:650}
div.stButton>button,div.stDownloadButton>button{border-radius:11px}
h1,h2,h3{letter-spacing:-.02em;color:#1a2a44}
header{background:transparent!important}
.hero{background:linear-gradient(107deg,#172844 0%,#273858 67%,#4a345b 100%);border-radius:19px;padding:30px 34px;margin:7px 0 24px;color:#f9fbff}
.hero h1{color:white;font-size:31px;margin:9px 0;line-height:1.16}
.hero p{color:#dce5f0;max-width:970px;line-height:1.64;margin:0;font-size:15px}
.eyebrow{color:#f8bdd8;letter-spacing:.11em;font-size:12px;font-weight:750;text-transform:uppercase}
.page-subtitle{color:#61718a;font-size:14px;margin:-10px 0 17px}
.footnote{font-size:12px;color:#8190a4;margin-top:25px;padding:13px 4px 5px;border-top:1px solid #e4e8f0}
[data-testid="stDataFrame"], [data-testid="stDataEditor"]{border-radius:12px;overflow:hidden}
</style>
''',unsafe_allow_html=True)

@st.cache_data(show_spinner=False)
def load_history():
    return pd.read_csv(ASSETS/'historial_ficticio_2026.csv',sep=';',encoding='utf-8-sig')

@st.cache_data(show_spinner=False)
def excel_bytes(df:pd.DataFrame, sheet='RESULTADOS'):
    out=BytesIO()
    with pd.ExcelWriter(out,engine='openpyxl',datetime_format='yyyy-mm-dd') as writer:
        df.to_excel(writer,sheet_name=sheet,index=False)
        sh=writer.book[sheet]
        sh.freeze_panes='A2'
        for cell in sh[1]:
            cell.font=__import__('openpyxl').styles.Font(bold=True,color='FFFFFF')
            cell.fill=__import__('openpyxl').styles.PatternFill('solid',fgColor='15243E')
        for column in sh.columns:
            letter=column[0].column_letter
            sh.column_dimensions[letter].width=min(38,max(16,max(len(str(c.value or '')) for c in list(column)[:250])+3))
    return out.getvalue()

@st.cache_data(show_spinner=False)
def read_uploaded_excel(content:bytes)->pd.DataFrame:
    try:
        df=pd.read_excel(BytesIO(content),sheet_name='REGISTROS_HOY',skiprows=3,engine='openpyxl')
    except Exception as exc:
        raise ValueError('El Excel debe tener la hoja REGISTROS_HOY de la plantilla oficial.') from exc
    df.columns=[str(c).strip() for c in df.columns]
    required=[COL['fecha'],COL['nombre']]
    missing=[f for f in required if f not in df.columns]
    if missing:raise ValueError('Faltan columnas: '+', '.join(missing))
    df=df.dropna(how='all').reset_index(drop=True)
    if len(df)>300:raise ValueError('La carga admite un máximo de 300 filas por operación.')
    for c in DAILY_COLUMNS:
        if c not in df.columns:df[c]=None
    return df[DAILY_COLUMNS]


def fresh_row(name=None,day=None):
    return {
        COL['fecha']:(day or date.today()).isoformat(),
        COL['prox']:((day or date.today())+timedelta(days=1)).isoformat(),
        COL['nombre']:name or available_players[0],
        COL['feel']:'Normal',COL['sleep']:'Bueno',
        COL['stress']:'Bajo', COL['fatigue']:'Normal',
        COL['soreness']:'Bajo',COL['hydration']:'Hidratada',
        COL['rpe']:5.0,COL['minutes']:75.0,COL['load']:375.0,
    }


def ensure_session():
    if 'hist' not in st.session_state:
        st.session_state.hist=load_history().copy()
    if 'register' not in st.session_state:
        st.session_state.register=[]
    if 'active_results' not in st.session_state:
        st.session_state.active_results=[]
    if 'editor_seed' not in st.session_state:
        st.session_state.editor_seed=pd.DataFrame([fresh_row()])[DAILY_COLUMNS]
    if 'editor_version' not in st.session_state:
        st.session_state.editor_version=0
    if 'last_upload_hash' not in st.session_state:
        st.session_state.last_upload_hash=None


def latest_dates_table(history):
    result=history.sort_values(COL['fecha']).drop_duplicates(COL['nombre'],keep='last')
    return result[[COL['nombre'],COL['fecha'],COL['rpe'],COL['load'],COL['fatigue']]].rename(columns={
        COL['nombre']:'Jugadora',COL['fecha']:'Última medición',COL['rpe']:'RPE',
        COL['load']:'Carga',COL['fatigue']:'Fatiga reportada'})


def update_editor(rows:pd.DataFrame):
    st.session_state.editor_seed=rows[DAILY_COLUMNS].reset_index(drop=True).copy()
    st.session_state.editor_version+=1


def run_batch(frame:pd.DataFrame):
    if len(frame)==0:raise ValueError('Agrega al menos una fila antes de predecir.')
    # Validación de todas las filas antes de guardar cualquier cosa.
    history=st.session_state.hist.copy()
    results=[]
    keys=set()
    for i, r in frame.iterrows():
        data=r.to_dict()
        name=str(data.get(COL['nombre'],'')).strip()
        day=pd.to_datetime(data.get(COL['fecha']),errors='coerce')
        if pd.isna(day): raise ValueError(f'Fila {i+1}: ingresa una fecha válida.')
        unique=(name,day.date())
        if unique in keys:raise ValueError(f'Hay más de una fila para {name} en {day.date()}.')
        keys.add(unique)
        try:
            result,completed=compute_forecast(data,history)
        except (ValueError,KeyError,TypeError) as exc:
            raise ValueError(f'Fila {i+1}: {exc}') from exc
        results.append(result)
        new_row=pd.DataFrame([completed])
        history=pd.concat([history,new_row],ignore_index=True)
        history=history.drop_duplicates([COL['nombre'],COL['fecha']],keep='last')
    # Todo válido: guardar al historial de la sesión y en el registro.
    st.session_state.hist=history
    st.session_state.active_results=results
    st.session_state.register.extend(results)
    return pd.DataFrame(results)


def source_download_buttons():
    sources=[('GPS','Plantilla_GPS.xlsx'),('Wellness y Carga','Plantilla_Wellness_y_Carga.xlsx'),
             ('Biomecánicos','Plantilla_Biomecanicos.xlsx'),('Laboratorio','Plantilla_Laboratorio.xlsx')]
    cols=st.columns(4)
    for col,(label,fname) in zip(cols,sources):
        with col:
            st.download_button(f'⬇ {label}',data=(TEMPLATES/fname).read_bytes(),
                file_name=fname,
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                use_container_width=True,key=f'src_{fname}')


# Estado de la aplicación solo en el navegador (sin almacenar información real)
available_players=roster(load_history())
ensure_session()
history=st.session_state.hist
current=date.today()

brand,version=st.columns([4,1],vertical_alignment='center')
with brand:
    st.markdown('### 🐉 DRAGONAS  <span style="color:#b83b79;font-weight:600;font-size:.75em">| IDV · USFQ</span>',unsafe_allow_html=True)
with version:
    st.caption('PANEL DE RENDIMIENTO')
page=st.radio('Secciones',['Inicio','Simulador','Registro de simulaciones'],
              horizontal=True,label_visibility='collapsed')
st.divider()

if page=='Inicio':
    st.markdown('''<div class="hero"><div class="eyebrow">Rendimiento deportivo · Bienestar y fatiga</div>
    <h1>Anticipa la próxima sesión</h1>
    <p>Visualiza el estado de tus jugadoras, incorpora las mediciones de la sesión actual y
    consulta una proyección de bienestar y fatiga para la siguiente. Todo desde un único panel.</p></div>''',unsafe_allow_html=True)
    next_day=st.date_input('Fecha de la próxima sesión',value=max(current, date(2026,11,10)),
                           help='Se utiliza como fecha objetivo del dashboard; la predicción usa la última observación disponible.')
    projected=forecast_latest(history,next_day)
    if projected.empty:
        st.info('No hay datos disponibles para la fecha indicada.')
    else:
        num=len(projected)
        avg=projected['Bienestar previsto'].mean()
        high=int((projected['Fatiga prevista']=='ALTA').sum())
        cols=st.columns(4)
        cols[0].metric('Jugadoras monitoreadas',num)
        cols[1].metric('Registros de 2026',len(history))
        cols[2].metric('Bienestar previsto · promedio',f'{avg:.1f} / 100')
        cols[3].metric('Fatiga alta · próxima sesión',high)
        st.markdown('#### Resumen del equipo')
        left,right=st.columns([1.0,1.12],gap='large')
        with left:
            with st.container(border=True):
                st.markdown('**Fatiga prevista por categoría**')
                fat_counts=projected['Fatiga prevista'].value_counts().reindex(['BAJA','MODERADA','ALTA'],fill_value=0)
                chart=pd.DataFrame({'Jugadoras':fat_counts})
                st.bar_chart(chart,height=260)
            with st.container(border=True):
                st.markdown('**Evolución semanal de carga**')
                last=history.copy()
                last['Semana']=pd.to_datetime(last[COL['fecha']],errors='coerce')
                last=last.dropna(subset=['Semana'])
                last=last[last['Semana']<=pd.Timestamp(next_day)]
                weekly=(last.groupby(pd.Grouper(key='Semana',freq='W'))[COL['load']]
                        .mean().tail(12).rename('Carga media'))
                st.line_chart(weekly,height=245)
        with right:
            with st.container(border=True):
                st.markdown('**Proyección individual · próxima sesión**')
                st.caption(f'Fecha objetivo: {next_day:%d/%m/%Y}')
                table=projected[['Jugadora','Bienestar previsto','Fatiga prevista','Fecha de registro']].copy()
                st.dataframe(table,hide_index=True,use_container_width=True,height=345,
                             column_config={'Bienestar previsto':st.column_config.ProgressColumn('Bienestar previsto',min_value=0,max_value=100,format='%.1f')})
                st.download_button('⬇ Descargar proyección del equipo',
                    data=excel_bytes(projected,'PROYECCION'),
                    file_name=f'proyeccion_dragonas_{next_day}.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    use_container_width=True)
            with st.container(border=True):
                st.markdown('**Actividad reciente**')
                st.dataframe(latest_dates_table(history).head(6),hide_index=True,
                             use_container_width=True,height=238)
    st.divider()
    col_1,col_2=st.columns([3,1],vertical_alignment='center')
    with col_1:
        st.markdown('**Historial de referencia · 2026**')
        st.caption('Incluye jugadoras ficticias y mediciones de Wellness, carga, GPS, biomecánica y laboratorio.')
    with col_2:
        st.download_button('⬇ Descargar historial 2026',
          data=(ASSETS/'Dragonas_Datos_Ficticios_2026.xlsx').read_bytes(),
          file_name='Dragonas_Datos_Ficticios_2026.xlsx',
          mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
          use_container_width=True)

elif page=='Simulador':
    st.markdown('''<div class="hero"><div class="eyebrow">Simulador · Próxima sesión</div>
    <h1>Registra hoy. Proyecta la siguiente sesión.</h1>
    <p>Ingresa una o varias jugadoras, completa sus datos actuales y obtén un resultado por cada registro.
    Puedes trabajar directamente en la tabla o cargar un archivo Excel.</p></div>''',unsafe_allow_html=True)
    section_l,section_r=st.columns([1.5,1],gap='large')
    with section_l:
        st.markdown('#### 1. Ingresar registros')
        st.caption('Una fila = una jugadora en una fecha. Agrega tantas filas como necesites.')
    with section_r:
        fmt_one,fmt_ten=st.columns(2)
        with fmt_one:
            st.download_button('⬇ Excel · 1 fila',
                 data=(TEMPLATES/'Plantilla_1_jugadora.xlsx').read_bytes(),
                 file_name='Plantilla_1_jugadora.xlsx',use_container_width=True,
                 mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        with fmt_ten:
            st.download_button('⬇ Excel · 10 filas',
                 data=(TEMPLATES/'Plantilla_10_jugadoras.xlsx').read_bytes(),
                 file_name='Plantilla_10_jugadoras.xlsx',use_container_width=True,
                 mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    st.caption('Esta página pública acepta únicamente datos de prueba y nombres ficticios.')
    uploader=st.file_uploader('Cargar registros en Excel (opcional)',type=['xlsx'],
                              help='Acepta las plantillas de 1 o 10 filas; puedes incluir más registros si necesitas.')
    if uploader is not None:
        content=uploader.getvalue()
        digest=sha256(content).hexdigest()
        if digest!=st.session_state.last_upload_hash:
            try:
                imported=read_uploaded_excel(content)
                if imported.empty:raise ValueError('El Excel no contiene registros.')
                update_editor(imported)
                st.session_state.last_upload_hash=digest
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
    else:
        st.session_state.last_upload_hash=None

    c1,c2=st.columns([1,1],vertical_alignment='center')
    with c1:
        if st.button('＋ Preparar 10 jugadoras',use_container_width=True):
            today=current
            update_editor(pd.DataFrame([fresh_row(n,today) for n in available_players[:10]]))
            st.rerun()
    with c2:
        if st.button('↺ Volver a una fila',use_container_width=True):
            update_editor(pd.DataFrame([fresh_row()]))
            st.rerun()
    cfg={
        COL['fecha']:st.column_config.TextColumn('Fecha (AAAA-MM-DD)',required=True,width='small'),
        COL['prox']:st.column_config.TextColumn('Próxima sesión (AAAA-MM-DD)',width='small'),
        COL['nombre']:st.column_config.SelectboxColumn('Jugadora',options=available_players,required=True,width='medium'),
        COL['rpe']:st.column_config.NumberColumn('RPE',min_value=1,max_value=10,step=.5,format='%.1f'),
        COL['minutes']:st.column_config.NumberColumn('Duración (min)',min_value=1,max_value=1440,step=1),
        COL['load']:st.column_config.NumberColumn('Carga',min_value=0,step=1),
    }
    for name,opts in CAT_CODES.items():
        cfg[name]=st.column_config.SelectboxColumn(name,options=list(opts),width='medium')
    edited=st.data_editor(st.session_state.editor_seed,
       key=f'editor_{st.session_state.editor_version}',num_rows='dynamic',
       hide_index=True,use_container_width=True,column_config=cfg,
       height=min(560,max(170,105+38*len(st.session_state.editor_seed))))
    st.caption('Los campos no medidos se completan con la mediana (numéricos) o moda (categorías) del historial previo. Si la carga está vacía, puede calcularse mediante RPE × duración.')
    if st.button('Predecir próxima sesión',type='primary',use_container_width=True):
        try:
            results=run_batch(edited)
            st.success(f'{len(results)} proyección(es) generada(s) correctamente.')
        except ValueError as exc:
            st.error(str(exc))
    if st.session_state.active_results:
        results=pd.DataFrame(st.session_state.active_results)
        st.markdown('#### 2. Resultados por jugadora')
        quick=st.columns(3)
        quick[0].metric('Registros procesados',len(results))
        quick[1].metric('Bienestar previsto medio',f'{results["Bienestar previsto"].mean():.1f} / 100')
        quick[2].metric('Fatiga alta',int((results['Fatiga prevista']=='ALTA').sum()))
        st.dataframe(results,hide_index=True,use_container_width=True,
            column_config={'Bienestar previsto':st.column_config.ProgressColumn('Bienestar previsto',min_value=0,max_value=100,format='%.1f')})
        st.download_button('⬇ Descargar resultados en Excel',type='primary',
            data=excel_bytes(results),
            file_name=f'proyecciones_dragonas_{current}.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            use_container_width=True)
    with st.expander('Plantillas adicionales por fuente'):
        st.caption('GPS, Wellness y Carga, Biomecánicos y Laboratorio. No es necesario completar estas fuentes para probar la proyección diaria.')
        source_download_buttons()
    with st.expander('Cómo se calcula la proyección'):
        st.write('Bienestar: regresión lineal múltiple usando fatiga reportada, sueño, estrés, dolor, hidratación, sensación, RPE y cargas actual e histórica de siete días. Fatiga: clasificación por puntuación.')
        st.caption('Los coeficientes fueron estimados mediante mínimos cuadrados sobre registros sintéticos; aún no existe validación del modelo con datos del club.')

elif page=='Registro de simulaciones':
    st.title('Registro de simulaciones')
    st.markdown('<p class="page-subtitle">Consulta y descarga las proyecciones generadas en esta sesión.</p>',unsafe_allow_html=True)
    results=pd.DataFrame(st.session_state.register)
    if results.empty:
        st.info('Todavía no se han generado proyecciones. Registra una sesión en Simulador para comenzar.')
    else:
        names=sorted(results['Jugadora'].unique())
        a,b=st.columns(2)
        with a: selected=st.selectbox('Jugadora',['Todas',*names])
        with b: level=st.selectbox('Fatiga',['Todas','BAJA','MODERADA','ALTA'])
        filtered=results.copy()
        if selected!='Todas':filtered=filtered[filtered['Jugadora']==selected]
        if level!='Todas':filtered=filtered[filtered['Fatiga prevista']==level]
        st.metric('Simulaciones mostradas',len(filtered))
        st.dataframe(filtered.iloc[::-1],hide_index=True,use_container_width=True,height=460)
        st.download_button('⬇ Descargar registro en Excel',
            data=excel_bytes(filtered,'REGISTRO'),file_name='registro_de_proyecciones.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            use_container_width=True)

st.markdown('<div class="footnote">Entorno con jugadoras y mediciones sintéticas. Las estimaciones no están validadas para decisiones médicas o deportivas.</div>',unsafe_allow_html=True)
