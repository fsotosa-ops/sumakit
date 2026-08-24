"""Configurador de tema: mueve los colores y ve el resultado al instante.

No es un editor de diagramación —eso es Canva y no vale la pena construirlo—.
Es el panel de perillas del sistema de diseño que ya existe en `theme.Palette`:
un solo objeto alimenta matplotlib, Altair, el PDF académico y los decks.

Lo que ninguna herramienta de diseño hace, y esta sí: **revalida la paleta en
cada cambio**. Si eliges dos colores que un lector con deuteranopía no
distingue, te lo dice ahí mismo, antes de que ese deck llegue a un cliente.

    sumakit theme
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import streamlit as st

# Absolutos y no relativos: `streamlit run` ejecuta este archivo como
# script suelto, sin paquete padre, y los relativos revientan.
from sumakit import theme

_ARCHIVO = "tema.json"
_CAMPOS_COLOR = [
    ("surface", "Fondo"),
    ("text_primary", "Texto principal"),
    ("text_secondary", "Texto secundario"),
    ("grid", "Grilla"),
    ("diverging_low", "Divergente: polo bajo"),
    ("diverging_high", "Divergente: polo alto"),
    ("neutral", "Divergente: centro"),
]


def _paleta_desde_estado(base: theme.Palette) -> theme.Palette:
    categorical = tuple(st.session_state.get(f"cat{i}", c) for i, c in enumerate(base.categorical))
    otros = {campo: st.session_state.get(campo, getattr(base, campo)) for campo, _ in _CAMPOS_COLOR}
    return theme.Palette(
        name=st.session_state.get("nombre", base.name),
        categorical=categorical,
        sequential=base.sequential,
        font_family=(st.session_state.get("fuente", base.font_family[0]),),
        **otros,
    )


def _figura_ejemplo(pal: theme.Palette):
    """Un gráfico real con el tema, no una muestra de colores."""
    with theme.using(pal):
        rng = np.random.default_rng(0)
        x = np.arange(12)
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9, 3.2))
        for i, etiqueta in enumerate(["Serie A", "Serie B", "Serie C"]):
            ax1.plot(x, np.cumsum(rng.normal(1, 1, 12)), label=etiqueta, color=pal.categorical[i])
        ax1.legend()
        ax1.set_title("Líneas")
        ax2.barh(list("abcde"), rng.uniform(2, 9, 5), color=pal.categorical[0])
        ax2.set_title("Barras")
        fig.tight_layout()
    return fig


def _lamina_ejemplo(pal: theme.Palette):
    """Boceto de una lámina con la misma geometría que usa `sumakit.deck`."""
    fig = plt.figure(figsize=(9, 5.06))
    fig.patch.set_facecolor(pal.surface)
    ax = fig.add_axes((0, 0, 1, 1))
    ax.set_axis_off()
    ax.set_xlim(0, 13.333)
    ax.set_ylim(0, 7.5)
    ax.invert_yaxis()

    ax.text(0.5, 0.55, "Principales hallazgos", fontsize=8, color=pal.text_secondary)
    ax.text(
        0.5,
        1.05,
        "Dos tercios de la cartera realizó tres transacciones",
        fontsize=13,
        color=pal.text_primary,
    )
    ax.text(0.5, 1.5, "o menos en el mes", fontsize=13, color=pal.categorical[0], fontweight="bold")
    ax.add_patch(plt.Rectangle((0.5, 1.9), 7.6, 4.7, facecolor=pal.grid, alpha=0.25))
    ax.add_patch(
        plt.Rectangle(
            (8.6, 2.1),
            4.2,
            1.2,
            facecolor=pal.surface,
            edgecolor=pal.categorical[0],
            linestyle="--",
            lw=1.4,
        )
    )
    ax.text(8.8, 2.6, "La anotación que dice\nqué mirar", fontsize=8.5, color=pal.text_primary)
    ax.add_patch(plt.Rectangle((0, 7.1), 13.333, 0.4, facecolor=pal.categorical[0]))
    return fig


def principal() -> None:
    """Corre el configurador de tema en Streamlit."""
    st.set_page_config(page_title="Tema · sumakit", layout="wide")
    base = theme.LIGHT

    st.sidebar.title("Tema")
    st.sidebar.text_input("Nombre", value=base.name, key="nombre")
    st.sidebar.selectbox(
        "Tipografía", ["Helvetica Neue", "Inter", "DejaVu Sans", "Georgia"], key="fuente"
    )
    if st.sidebar.button("Partir del tema oscuro"):
        for i, c in enumerate(theme.DARK.categorical):
            st.session_state[f"cat{i}"] = c
        for campo, _ in _CAMPOS_COLOR:
            st.session_state[campo] = getattr(theme.DARK, campo)
        st.rerun()

    st.sidebar.subheader("Serie categórica")
    st.sidebar.caption(
        "El orden es el mecanismo de seguridad para daltonismo, "
        "no decoración: se asignan siempre desde el primero."
    )
    for i, c in enumerate(base.categorical):
        st.sidebar.color_picker(f"Slot {i + 1}", value=c, key=f"cat{i}")

    st.sidebar.subheader("Superficies")
    for campo, etiqueta in _CAMPOS_COLOR:
        st.sidebar.color_picker(etiqueta, value=getattr(base, campo), key=campo)

    pal = _paleta_desde_estado(base)

    izq, der = st.columns([3, 2])
    with izq:
        st.subheader("Gráficos")
        st.pyplot(_figura_ejemplo(pal))
        st.subheader("Lámina")
        st.pyplot(_lamina_ejemplo(pal))

    with der:
        st.subheader("Validación")
        st.caption("Se recalcula en cada cambio. Ninguna herramienta de diseño revisa esto por ti.")
        modo = st.radio(
            "Forma del gráfico",
            ["Barras y líneas", "Scatter y pairplot"],
            horizontal=True,
            help="Un scatter compara todas las series a la vez y es "
            "mucho más exigente que unas barras.",
        )
        n = st.slider("Series simultáneas", 2, 8, 5)
        try:
            informe = theme.validate(pal, n=n, all_pairs=modo.startswith("Scatter"))
        except ValueError as e:
            st.error(str(e))
        else:
            for _, fila in informe.iterrows():
                icono = "✅" if fila["pasa"] else "⚠️"
                st.markdown(
                    f"{icono} **{fila['chequeo']}** — {fila['valor']} (mínimo {fila['umbral']})"
                )
                st.caption(fila["detalle"])

        st.divider()
        st.subheader("Guardar")
        destino = st.text_input("Archivo", value=_ARCHIVO)
        if st.button("Escribir el tema", type="primary"):
            ruta = Path(destino)
            ruta.write_text(
                json.dumps(_serializar(pal), indent=2, ensure_ascii=False), encoding="utf-8"
            )
            st.success(f"Escrito en {ruta.resolve()}")
            st.code(
                f'from sumakit import theme\ntheme.use(theme.load("{ruta}"))', language="python"
            )


def _serializar(pal: theme.Palette) -> dict:
    return {
        "name": pal.name,
        "categorical": list(pal.categorical),
        "sequential": list(pal.sequential),
        "diverging_low": pal.diverging_low,
        "diverging_high": pal.diverging_high,
        "neutral": pal.neutral,
        "surface": pal.surface,
        "text_primary": pal.text_primary,
        "text_secondary": pal.text_secondary,
        "grid": pal.grid,
        "font_family": list(pal.font_family),
    }


if __name__ == "__main__":
    principal()
