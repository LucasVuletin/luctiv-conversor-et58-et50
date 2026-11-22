"""Ejecutar: streamlit run app.py"""
import streamlit as st
from conversor import convertir_csv, indicadores, nombre_descarga
from grafico import crear_grafico, registros_base

st.set_page_config(page_title="Variables WRST → YPF", page_icon="🛢️", layout="wide")
st.title("Conversor de variables WRST a variables para YPF")
st.caption("CSV WRST → estructura INSITE del CSV base para YPF")

izquierda, derecha = st.columns(2)
with izquierda:
    base = st.file_uploader(
        "1. CSV base para YPF (INSITE)", type=["csv"], key="base",
        help="Se usan sus 15 filas de encabezado, nombres, unidades y orden de canales.",
    )
with derecha:
    archivo = st.file_uploader(
        "2. CSV WRST a convertir (Treatment Data Publisher)",
        type=["csv"], key="origen",
    )
with st.expander("Configuración y origen de los datos"):
    desfase = st.number_input("Desfase de UTC (horas)", min_value=-12, max_value=14, value=-3)
    st.caption("El archivo base debe tener el esquema INSITE de 51 columnas físicas. "
               "El TDP de referencia tiene 70 columnas físicas. "
               "Los factores estimados proceden de la homologación previa del ELG-137.")

if base is not None and archivo is not None:
    try:
        contenido, registros, nombres = convertir_csv(
            archivo.getvalue(), base.getvalue(), desfase
        )
        kpi = indicadores(registros)
    except (ValueError, IndexError, UnicodeError, OSError) as error:
        st.error(f"No se pudo convertir el archivo: {error}")
        st.stop()

    st.success(f"Archivo generado: {kpi['registros']:,} registros y {len(nombres)} columnas, "
               "con el orden y encabezado del CSV base.")
    st.subheader("Señales operativas en un solo gráfico")
    base_registros = registros_base(base.getvalue())
    escala_pct = st.slider(
        "Escala vertical de todos los ejes (%)", min_value=100, max_value=300,
        value=150, step=10,
        help="100 % ajusta cada eje a sus datos; bajá el valor para acercar "
             "o subilo para dejar más espacio. "
             "Las unidades de los cinco ejes se mantienen independientes.",
    )
    opciones = ["Archivo convertido para YPF"]
    if base_registros:
        opciones.append("Archivo base para YPF")
    seleccion = st.radio("Datos a visualizar", opciones, horizontal=True)
    convertido = seleccion == "Archivo convertido para YPF"
    datos_grafico = registros if convertido else base_registros
    try:
        st.plotly_chart(
            crear_grafico(datos_grafico, seleccion, proxy_fr=convertido,
                          escala=escala_pct / 100),
            use_container_width=True,
            config={"displaylogo": False},
        )
    except ValueError as error:
        st.warning(f"No se pudo graficar: {error}")
    st.caption("Los dos canales de arena comparten el eje lb/gal. Presión, caudal, "
               "FR líquido y FR sólido tienen escalas independientes con sus propias unidades. "
               "En el archivo convertido, FR sólido es un **proxy FDP-S1278-17**, "
               "no una medición de FightR LXD.")

    st.subheader("Indicadores operativos · calculados sobre el CSV final")
    col1, col2, col3 = st.columns(3)
    col1.metric("Caudal promedio bombeando", f"{kpi['caudal_prom_bpm']:,.1f} bpm")
    col2.metric("Presión promedio bombeando", f"{kpi['presion_prom_psi']:,.0f} psi")
    col3.metric("Concentración promedio con arena", f"{kpi['conc_arena_prom_lbgal']:,.2f} lb/gal")
    col4, col5, col6 = st.columns(3)
    col4.metric("Arena total", f"{kpi['arena_total_tn']:,.1f} toneladas")
    col5.metric("Volumen slurry acumulado", f"{kpi['volumen_slurry_bbl']:,.0f} bbl")
    col6.metric("Tiempo bombeando", f"{kpi['duracion_bombeo_min']:,.1f} min")

    st.caption("Promedios de caudal y presión: sólo muestras con CAUDAL_SLURRY > 5 bpm. "
               "Concentración: además, CONC_SLURRY > 0,05 lb/gal. "
               "Arena: AS_TOTAL (100×lb) convertido a toneladas métricas. "
               "Duración bombeando: muestras a 1 Hz / 60.")

    st.subheader("Controles de consistencia")
    a, b, c = st.columns(3)
    a.metric("Arena por integración del dosificador", f"{kpi['arena_integrada_lb']:,.0f} lb")
    b.metric("Arena por acumulador", f"{kpi['arena_total_lb']:,.0f} lb")
    c.metric("Diferencia de arena", f"{kpi['error_arena_pct']:.4f} %")
    if kpi["muestreo_1s"] and not kpi["contador_arena_retrocesos"] and kpi["error_arena_pct"] < 1:
        st.success("Control OK: muestreo de 1 segundo, arena acumulada sin retrocesos "
                   "y diferencia de integración inferior al 1 %.")
    else:
        st.warning("Revisar: el muestreo no es uniforme de 1 segundo, el acumulador "
                   "retrocede o la integración de arena difiere ≥1 %. "
                   "El control de integración presupone muestras a 1 Hz.")

    nombre_salida = nombre_descarga(archivo.name)
    st.download_button("⬇️ Descargar CSV terminado (51 columnas)", contenido,
                       file_name=nombre_salida, mime="text/csv", type="primary")

    with st.expander("Vista previa de los valores generados"):
        columnas = [0, 2, 6, 14, 15, 23, 31, 34]
        st.dataframe([{nombres[i]: f[i] for i in columnas} for f in registros[:30]],
                     use_container_width=True, hide_index=True)
        st.caption("Se muestran las primeras 30 filas; el CSV descargable incluye todos los registros.")

    st.info("**Trazabilidad:** los canales sin medición en el origen se dejan en 0 "
            "(no equivale a una lectura de sensor). Algunos canales se estiman a partir "
            "de los factores previos. 'FightR LXD' usa FDP-S1278-17 por compatibilidad de unidades, "
            "no por equivalencia química.")
else:
    st.info("Subí el CSV base para YPF y el TDP WRST para convertir y graficar.")
