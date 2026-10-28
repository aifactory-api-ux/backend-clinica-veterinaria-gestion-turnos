"""Dependencias compartidas por los endpoints protegidos de la API.

``get_current_user`` resuelve el usuario autenticado a partir de la cabecera
``Authorization: Bearer <jwt>``. Cualquier fallo (cabecera ausente o con otro
esquema, token mal formado, firmado con otra clave, caducado o de un usuario
que ya no existe) se traduce en una respuesta ``401``.
"""

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.database import get_db
from app.errors import AuthenticationError
from app.models import User
from app.security import decode_access_token
from app.services import users

# Esquema de autorización admitido en la cabecera ``Authorization``.
ESQUEMA_PORTADOR = "Bearer"


def _extraer_token(cabecera: str | None) -> str:
    """Extrae el token de una cabecera ``Authorization: Bearer <token>``."""
    if not cabecera:
        raise AuthenticationError("Falta la cabecera Authorization.")

    partes = cabecera.split()
    if len(partes) != 2 or partes[0].lower() != ESQUEMA_PORTADOR.lower():
        raise AuthenticationError(
            "La cabecera Authorization debe usar el esquema Bearer."
        )

    return partes[1]


def get_current_user(
    authorization: str | None = Header(default=None),
    session: Session = Depends(get_db),
) -> User:
    """Devuelve la cuenta autenticada a partir del token Bearer presentado.

    El rol y los permisos se toman siempre de la base de datos, no del token,
    para que un token antiguo no pueda ampliar los privilegios de una cuenta.
    """
    token = _extraer_token(authorization)
    claims = decode_access_token(token)

    try:
        user_id = int(claims["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise AuthenticationError("El token no identifica a ninguna cuenta.") from exc

    usuario = users.buscar_usuario_por_id(session, user_id)
    if usuario is None:
        raise AuthenticationError("La cuenta del token no existe.")
    return usuario
