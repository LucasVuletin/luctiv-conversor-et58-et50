"""Gráfico operativo de cinco escalas para datos INSITE."""

import math

import plotly.graph_objects as go

from conversor import N_CANALES, leer_csv


SERIES = (
    ("Presión", 2, "y", "#e45756", "psi"),
    ("Caudal", 6, "y2", "#277da1", "bpm"),
    ("Arena en superficie", 31, "y3", "#f8961e", "lb/gal"),
    ("Arena en fondo", 32, "y3", "#9c6644", "lb/gal"),
    ("FR líquido", 37, "y4", "#43aa8b", "gal/Mgal"),
    ("FR sólido (proxy)", 39, "y5", "#9b5de5", "lb/Mgal"),
)


def registros_base(contenido):
    """Lee las muestras del CSV INSITE usado como base."""
    return [
        fila for fila in leer_csv(contenido)[15:]
        if len(fila) == N_CANALES
    ]


def _numero_o_nulo(valor):
    try:
        resultado = float(valor)
    except (TypeError, ValueError):
        return None
    return resultado if math.isfinite(resultado) else None


def _reducir_extremos(x, y, max_puntos=6000):
    """Reduce series largas conservando picos y valles por intervalo."""
    if len(x) <= max_puntos:
        return x, y
    tam = math.ceil(len(x) / (max_puntos // 2))
    indices = {0, len(x) - 1}
    for inicio in range(0, len(x), tam):
        fin = min(inicio + tam, len(x))
        validos = [i for i in range(inicio, fin) if y[i] is not None]
        if validos:
            indices.add(min(validos, key=lambda i: y[i]))
            indices.add(max(validos, key=lambda i: y[i]))
    orden = sorted(indices)
    return [x[i] for i in orden], [y[i] for i in orden]


def _rango(series, escala=1.0):
    valores = [v for datos in series for v in datos if v is not None]
    if not valores:
        return [0, 1]
    minimo, maximo = min(valores), max(valores)
    if minimo >= 0:
        return [0, (maximo * 1.08 if maximo > 0 else 1) * escala]
    margen = (maximo - minimo) * 0.06 or 1
    return [(minimo - margen) * escala, (maximo + margen) * escala]


def crear_grafico(registros, titulo, proxy_fr=True, escala=1.0):
    """Superpone seis señales sobre cinco ejes con sus unidades originales."""
    puntos = [
        (x, fila) for fila in registros
        if len(fila) == N_CANALES
        if (x := _numero_o_nulo(fila[1])) is not None
    ]
    if not puntos:
        raise ValueError("No hay muestras con tiempo válido para graficar.")
    inicio = puntos[0][0]
    x = [punto[0] - inicio for punto in puntos]
    ejes = {"y": [], "y2": [], "y3": [], "y4": [], "y5": []}
    figura = go.Figure()
    for nombre, columna, eje, color, unidad in SERIES:
        if columna == 39 and not proxy_fr:
            nombre = "FR sólido"
        y = [_numero_o_nulo(fila[columna]) for _, fila in puntos]
        ejes[eje].append(y)
        x_reducido, y_reducido = _reducir_extremos(x, y)
        figura.add_trace(go.Scattergl(
            x=x_reducido, y=y_reducido, mode="lines", name=nombre,
            yaxis=eje, line={"color": color, "width": 1.7},
            hovertemplate=(f"{nombre}: %{{y:,.2f}} {unidad}<br>"
                           "Tiempo transcurrido: %{x:,.2f} min<extra></extra>"),
        ))

    figura.update_layout(
        title=titulo,
        xaxis={"title": "Tiempo transcurrido (min)", "domain": [0.19, 0.67],
               "showgrid": True, "gridcolor": "#e8edf2"},
        yaxis={"title": {"text": "Presión (psi)", "font": {"color": "#e45756"}},
               "range": _rango(ejes["y"], escala), "tickfont": {"color": "#e45756"},
               "tickformat": ",.0f", "nticks": 6},
        yaxis2={"title": {"text": "Caudal (bpm)", "font": {"color": "#277da1"}},
                "range": _rango(ejes["y2"], escala), "tickformat": ",.1f", "nticks": 6,
                "overlaying": "y", "side": "right", "anchor": "free", "position": 0.67,
                "tickfont": {"color": "#277da1"},
                "showgrid": False},
        yaxis3={"title": {"text": "Arena (lb/gal)", "font": {"color": "#f8961e"}},
                "range": _rango(ejes["y3"], escala), "tickformat": ",.2f", "nticks": 6,
                "overlaying": "y", "side": "left", "anchor": "free", "position": 0.07,
                "tickfont": {"color": "#f8961e"},
                "showgrid": False},
        yaxis4={"title": {"text": "FR líquido (gal/Mgal)", "font": {"color": "#43aa8b"}},
                "range": _rango(ejes["y4"], escala), "tickformat": ",.1f", "nticks": 6,
                "overlaying": "y", "side": "right", "anchor": "free", "position": 0.80,
                "tickfont": {"color": "#43aa8b"},
                "showgrid": False},
        yaxis5={"title": {"text": "FR sólido proxy (lb/Mgal)" if proxy_fr
                           else "FR sólido (lb/Mgal)", "font": {"color": "#9b5de5"}},
                "range": _rango(ejes["y5"], escala), "tickformat": ",.1f", "nticks": 6,
                "overlaying": "y", "side": "right", "anchor": "free", "position": 0.93,
                "tickfont": {"color": "#9b5de5"},
                "showgrid": False},
        legend={"orientation": "h", "y": 1.14, "x": 0.5, "xanchor": "center"},
        height=610, margin={"l": 80, "r": 105, "t": 105, "b": 65},
        hovermode="x", template="plotly_white",
    )
    return figura
