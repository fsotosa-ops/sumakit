"""Nombres viejos que siguen funcionando, con aviso.

La API pública de un SDK es un contrato con gente a la que no puedes llamar: hay
notebooks de Colab con `studio.conectar(...)` escrito dentro. Renombrar es
correcto —la mezcla de idiomas era el defecto— pero romperlos en silencio es
peor que la inconsistencia que el renombre vino a arreglar.

Este módulo es privado a propósito. Cuando los alias se retiren, se borra entero
y el `import` que quede señala qué falta por limpiar.
"""

from __future__ import annotations

import warnings
from collections.abc import Callable
from typing import Any, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


def deprecated_alias(new: F, old_name: str, new_name: str, *, module: str = "") -> F:
    """Devuelve una copia de `new` que avisa antes de llamar.

    Args:
        new: La función con el nombre nuevo, que es la que hace el trabajo.
        old_name: El nombre viejo, el que alguien tiene escrito en su notebook.
        new_name: El nombre nuevo, para decirle a qué migrar.
        module: Prefijo para el mensaje, p. ej. `"studio"`.

    Returns:
        Un envoltorio con la misma firma que emite `DeprecationWarning`.
    """
    prefijo = f"{module}." if module else ""

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        warnings.warn(
            f"{prefijo}{old_name}() se renombró a {prefijo}{new_name}()",
            DeprecationWarning,
            stacklevel=2,
        )
        return new(*args, **kwargs)

    wrapper.__name__ = old_name
    wrapper.__qualname__ = old_name
    wrapper.__doc__ = f"Obsoleto: usa `{new_name}`."
    return wrapper  # type: ignore[return-value]
