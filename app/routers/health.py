"""Comprobación pública de disponibilidad de la API."""

from fastapi import APIRouter

router = APIRouter(tags=["salud"])


@router.get("/health", summary="Comprobación de estado del servicio")
def comprobar_salud() -> dict[str, str]:
    """Indica que el servicio está en línea.

    Es un endpoint público: no exige cabecera ``Authorization``, por lo que
    un token ausente o inválido no altera la respuesta.
    """
    return {"status": "ok"}
