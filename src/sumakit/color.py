"""Aritmética de color: contraste, separación perceptual y daltonismo.

Existe para que el configurador de temas pueda impedir una paleta mala en vez
de advertirla después. Elegir colores "a ojo" es exactamente donde se cuela un
par que un lector con deuteranopía —cerca del 6% de los hombres— no distingue,
o un amarillo que no se lee sobre fondo claro.

Todo el cálculo es determinista y está en numpy: no hay servicio externo.
"""

from __future__ import annotations

import numpy as np

__all__ = [
    "a_rgb", "luminancia", "contraste", "a_lab", "delta_e", "simular_cvd",
    "TIPOS_CVD",
]

#: Matrices de simulación sobre RGB lineal (Machado, Oliveira & Fernandes).
TIPOS_CVD = {
    "protanopía": np.array([
        [0.152286, 1.052583, -0.204868],
        [0.114503, 0.786281, 0.099216],
        [-0.003882, -0.048116, 1.051998],
    ]),
    "deuteranopía": np.array([
        [0.367322, 0.860646, -0.227968],
        [0.280085, 0.672501, 0.047413],
        [-0.011820, 0.042940, 0.968881],
    ]),
    "tritanopía": np.array([
        [1.255528, -0.076749, -0.178779],
        [-0.078411, 0.930809, 0.147602],
        [0.004733, 0.691367, 0.303900],
    ]),
}

# sRGB D65 -> XYZ
_M_XYZ = np.array([
    [0.4124564, 0.3575761, 0.1804375],
    [0.2126729, 0.7151522, 0.0721750],
    [0.0193339, 0.1191920, 0.9503041],
])
_BLANCO_D65 = np.array([0.95047, 1.00000, 1.08883])


def a_rgb(hexa: str) -> np.ndarray:
    """'#2a78d6' -> array [0,1] de tres componentes."""
    h = hexa.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        raise ValueError(f"color hexadecimal inválido: {hexa!r}")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], dtype=float) / 255.0


def _lineal(rgb: np.ndarray) -> np.ndarray:
    """Deshace la corrección gamma de sRGB. La luz se suma en lineal, no en sRGB."""
    return np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)


def _gamma(lineal: np.ndarray) -> np.ndarray:
    return np.where(lineal <= 0.0031308, lineal * 12.92,
                    1.055 * np.clip(lineal, 0, None) ** (1 / 2.4) - 0.055)


def luminancia(color: str) -> float:
    """Luminancia relativa según WCAG."""
    return float(np.dot(_lineal(a_rgb(color)), [0.2126, 0.7152, 0.0722]))


def contraste(uno: str, otro: str) -> float:
    """Razón de contraste WCAG, entre 1 (idénticos) y 21 (blanco sobre negro)."""
    a, b = sorted((luminancia(uno), luminancia(otro)), reverse=True)
    return (a + 0.05) / (b + 0.05)


def a_lab(color: str | np.ndarray) -> np.ndarray:
    """Convierte a CIE L*a*b*.

    Es el espacio donde la distancia euclidiana aproxima la diferencia que
    percibe el ojo, y por eso se usa para medir si dos colores se distinguen.
    """
    rgb = a_rgb(color) if isinstance(color, str) else np.asarray(color, dtype=float)
    xyz = _M_XYZ @ _lineal(rgb) / _BLANCO_D65
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.array([116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2])])


def delta_e(uno, otro) -> float:
    """Diferencia perceptual CIE76. Bajo ~15 dos colores se confunden."""
    return float(np.linalg.norm(a_lab(uno) - a_lab(otro)))


def simular_cvd(color: str, tipo: str) -> np.ndarray:
    """Cómo ve ese color alguien con el tipo de daltonismo indicado."""
    if tipo not in TIPOS_CVD:
        raise ValueError(f"tipo debe ser uno de {sorted(TIPOS_CVD)}; no {tipo!r}")
    return _gamma(np.clip(TIPOS_CVD[tipo] @ _lineal(a_rgb(color)), 0, 1))
