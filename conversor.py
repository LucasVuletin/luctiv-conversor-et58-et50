"""Conversor TDP -> formato INSITE de 51 canales (etapa base).
Sin pandas: preserva encabezados, columnas, unidades y posiciones del CSV.
Los coeficientes reproducen la homologación validada del ELG-137 ET58.
"""
import csv
import io
import re
from datetime import datetime, timedelta
from pathlib import Path
from esquema import ESQUEMA_INSITE

# Posición de destino (0-based) -> nombre de canal de la fuente TDP.
DIRECTOS = {
    2: "Treating Pressure", 3: "Treating Pressure @Pump",
    4: "Backside Pressure", 5: "Hydrostatic Pressure",
    6: "Slurry Rate", 8: "B2 LA 1 Rate",
    10: "B1 Dirty Magnetic FM Rate", 11: "Clean Rate",
    13: "Slurry Rate", 14: "Job Clean Vol", 15: "Job Slurry Vol",
    17: "Slurry Density", 18: "Slurry Density",
    26: "B1 SS 1 Conc", 27: "B1 SS 2 Conc",
    30: "Wellhead Proppant Conc", 31: "Slurry Proppant Conc",
    32: "BH Proppant Conc", 34: "Job Proppant",
    37: "FightR EC-3 Conc", 38: "FightR EC-3 Rate",
    39: "FDP-S1278-17 Conc", 40: "FDP-S1278-17 Rate",
    41: "SP Breaker Conc", 42: "SP Breaker Rate",
    48: "Slurry Proppant Conc", 49: "Slurry Proppant Conc",
}
# Coeficientes calibrados contra el 136; no representan sensores nuevos.
F_CONC_BLENDER = 3.81697683941652
F_DENS_BATEA = 0.4885913216751961
F_RPM_TORNILLO = 0.01973176249264755
F_CAUDAL_CLEAN_BL = 0.4781237927074924
C_REAL_CLEAN = 1.269730475
FMT_HORA = "%d-%b-%Y %H:%M:%S"
N_CANALES = 51


def leer_csv(contenido):
    """Acepta bytes de Streamlit o un path; mantiene filas vacías."""
    if isinstance(contenido, (str, Path)):
        contenido = Path(contenido).read_bytes()
    texto = contenido.decode("utf-8-sig")
    return list(csv.reader(io.StringIO(texto, newline="")))


def numero(valor):
    return float(valor) if valor else 0.0


def texto_num(valor):
    return f"{valor:.10g}"


def nombre_descarga(nombre_origen):
    """Conserva pozo y etapa del nombre de origen y marca el formato YPF."""
    etapa = re.search(r"_(\d+)_", nombre_origen)
    numero_etapa = etapa.group(1) if etapa else "XX"
    pozo = re.search(r"ELG-\d+(?:\([^)]*\))?", nombre_origen, re.I)
    nombre_pozo = pozo.group() if pozo else "POZO"
    return f"YPF.Nq.{nombre_pozo}_ET{numero_etapa}_FORMATO_YPF.csv"


def convertir_csv(origen, plantilla, desfase_horas=-3):
    """Devuelve (bytes CSV compatibles, registros finales, nombres columnas).

    El origen usa 70 canales (TDP), la plantilla conserva el encabezado
    y el orden de 51 canales (INSITE). Se descartan eventos de 3 campos.
    """
    src, tpl = leer_csv(origen), leer_csv(plantilla)
    if len(src) < 16 or len(tpl) < 15:
        raise ValueError("Los archivos no contienen los encabezados esperados.")
    nombres_src, nombres_dst = src[13], tpl[13]
    if len(nombres_dst) != N_CANALES or len(tpl[14]) != N_CANALES:
        raise ValueError("El CSV base debe tener 51 canales INSITE en las filas 14 y 15.")
    incompatibles = [
        f"{pos + 1}: {nombre} {unidad}"
        for pos, (nombre, unidad) in enumerate(ESQUEMA_INSITE)
        if (nombres_dst[pos], tpl[14][pos]) != (nombre, unidad)
    ]
    if incompatibles:
        raise ValueError(
            "El CSV base no coincide con el esquema INSITE esperado en las columnas "
            + ", ".join(incompatibles)
        )
    idx = {nombre: pos for pos, nombre in enumerate(nombres_src)}
    requeridos = set(DIRECTOS.values()) | {"Stage At Blender", "Clean Density"}
    faltantes = sorted(requeridos.difference(idx))
    if faltantes:
        raise ValueError("Faltan canales en el origen: " + ", ".join(faltantes))
    serie = [fila for fila in src[15:] if len(fila) == len(nombres_src)]
    if not serie:
        raise ValueError("No se encontraron registros operativos en el origen.")

    primera = datetime.strptime(serie[0][0], FMT_HORA)
    primera_local = primera + timedelta(hours=desfase_horas)
    pozo = src[4][0].strip() if src[4] else "POZO"
    match = re.search(r"-(\d+)", pozo)
    numero_pozo = match.group(1) if match else ""

    cab = [fila.copy() for fila in tpl[:15]]
    cab[0][-1] = str(N_CANALES)
    cab[1] = [f"UTC{desfase_horas:+g}"]
    cab[4] = [f"{pozo} {numero_pozo}".strip()]
    cab[7] = [primera_local.strftime("%d-%b-%Y")]
    cab[8] = [src[9][0] if len(src) > 9 and src[9] else ""]

    resultado = []
    etapa_anterior, volumen_inicio_etapa = None, 0.0
    for fila in serie:
        datos = ["0"] * N_CANALES
        for posicion, nombre in DIRECTOS.items():
            datos[posicion] = fila[idx[nombre]] or "0"

        actual = datetime.strptime(fila[0], FMT_HORA)
        datos[0] = (actual + timedelta(hours=desfase_horas)).strftime(FMT_HORA)
        datos[1] = texto_num((actual - primera).total_seconds() / 60)

        limpio = numero(fila[idx["Clean Rate"]])
        sucio = numero(fila[idx["B1 Dirty Magnetic FM Rate"]])
        conc = numero(fila[idx["Slurry Proppant Conc"]])
        dens_limpia = numero(fila[idx["Clean Density"]])
        volumen = numero(fila[idx["Job Slurry Vol"]])
        etapa = fila[idx["Stage At Blender"]]
        if etapa != etapa_anterior:
            etapa_anterior, volumen_inicio_etapa = etapa, volumen

        suc_uh = max(limpio - sucio, 0.0)
        caudal_bl = suc_uh * F_CAUDAL_CLEAN_BL
        conc_bl = conc * F_CONC_BLENDER
        arena_rate = conc * limpio * 42  # lb/gal * bpm * gal/bbl = lb/min
        rpm = arena_rate * F_RPM_TORNILLO

        datos[7] = texto_num(suc_uh)
        datos[9] = texto_num(caudal_bl)
        datos[12] = texto_num(
            limpio + sucio + caudal_bl
            - min(max(limpio / 60, 0), 1) * C_REAL_CLEAN
        )
        datos[16] = texto_num(max(volumen - volumen_inicio_etapa, 0))
        datos[19] = texto_num(dens_limpia + conc_bl * F_DENS_BATEA)
        datos[20] = datos[47] = texto_num(rpm)
        datos[23] = datos[46] = texto_num(arena_rate)
        datos[29] = datos[33] = texto_num(conc_bl)
        resultado.append(datos)

    buffer = io.StringIO(newline="")
    csv.writer(buffer, lineterminator="\r\n").writerows(cab + resultado)
    return buffer.getvalue().encode("utf-8"), resultado, nombres_dst


def indicadores(registros):
    """KPIs leídos EXCLUSIVAMENTE de las columnas del CSV terminado."""
    if not registros:
        raise ValueError("La salida está vacía.")
    bombeando = [fila for fila in registros if numero(fila[6]) > 5]  # >5 bpm
    con_arena = [fila for fila in bombeando if numero(fila[31]) > 0.05]
    promedio = lambda filas, col: sum(numero(f[col]) for f in filas) / len(filas) if filas else 0.0
    arena_lb = max(numero(fila[34]) for fila in registros) * 100
    arena_integrada_lb = sum(numero(fila[23]) for fila in registros) / 60  # 1 muestra/seg
    error = abs(arena_integrada_lb - arena_lb) / arena_lb * 100 if arena_lb else 0
    intervalos = [
        (datetime.strptime(b[0], FMT_HORA) - datetime.strptime(a[0], FMT_HORA)).total_seconds()
        for a, b in zip(registros, registros[1:])
    ]
    dt_1s = bool(intervalos) and all(s == 1 for s in intervalos)
    regresiones = sum(numero(b[34]) + 1e-6 < numero(a[34]) for a, b in zip(registros, registros[1:]))
    return {
        "registros": len(registros),
        "caudal_prom_bpm": promedio(bombeando, 6),
        "presion_prom_psi": promedio(bombeando, 2),
        "conc_arena_prom_lbgal": promedio(con_arena, 31),
        "arena_total_lb": arena_lb,
        "arena_total_tn": arena_lb * 0.45359237 / 1000,
        "arena_integrada_lb": arena_integrada_lb,
        "error_arena_pct": error,
        "volumen_limpio_bbl": max(numero(f[14]) for f in registros) / 42,
        "volumen_sucio_gal": max(numero(f[15]) for f in registros),
        "volumen_slurry_bbl": max(numero(f[15]) for f in registros) / 42,
        "duracion_bombeo_min": len(bombeando) / 60,
        "duracion_total_min": (datetime.strptime(registros[-1][0], FMT_HORA) - datetime.strptime(registros[0][0], FMT_HORA)).total_seconds() / 60,
        "presion_max_psi": max(numero(f[2]) for f in registros),
        "caudal_max_bpm": max(numero(f[6]) for f in registros),
        "muestreo_1s": dt_1s,
        "contador_arena_retrocesos": regresiones,
        "muestras_bombeando": len(bombeando),
        "muestras_con_arena": len(con_arena),
    }
