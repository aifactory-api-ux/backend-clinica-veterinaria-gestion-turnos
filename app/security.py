"""Primitivas de seguridad de la API: hash de contraseñas y tokens JWT.

El hash de contraseñas usa PBKDF2-HMAC-SHA256 con una sal aleatoria por usuario
y 200 000 iteraciones, en el formato ``pbkdf2_sha256$<iteraciones>$<sal>$<hash>``.
Los tokens de acceso son JWT firmados con HS256 que transportan los ``claims``
``sub`` (identificador del usuario), ``role``, ``iat`` y ``exp``.
"""

import hashlib
import hmac
import secrets
from datetime import datetime, timezone
from typing import Any

from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError

from app.config import JWT_ALGORITHM, settings
from app.errors import AuthenticationError

# Parámetros del hash de contraseñas.
PASSWORD_SCHEME = "pbkdf2_sha256"
PBKDF2_ITERATIONS = 200_000
PASSWORD_SALT_BYTES = 16


class InvalidTokenError(AuthenticationError):
    """El token presentado no es un JWT válido emitido por este servicio."""

    default_detail = "Token de acceso inválido."


class ExpiredTokenError(AuthenticationError):
    """El token presentado ya ha caducado."""

    default_detail = "El token de acceso ha expirado."


def hash_password(password: str) -> str:
    """Deriva el hash de una contraseña con PBKDF2-HMAC-SHA256 y sal aleatoria."""
    salt = secrets.token_bytes(PASSWORD_SALT_BYTES)
    derivada = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS
    )
    return f"{PASSWORD_SCHEME}${PBKDF2_ITERATIONS}${salt.hex()}${derivada.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    """Comprueba la contraseña contra el hash almacenado, en tiempo constante."""
    if not password_hash:
        return False

    partes = password_hash.split("$")
    if len(partes) != 4:
        return False

    esquema, iteraciones, sal_hex, esperado_hex = partes
    if esquema != PASSWORD_SCHEME:
        return False

    try:
        numero_iteraciones = int(iteraciones)
        salt = bytes.fromhex(sal_hex)
        esperado = bytes.fromhex(esperado_hex)
    except ValueError:
        return False

    derivada = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, numero_iteraciones
    )
    return hmac.compare_digest(derivada, esperado)


def create_access_token(
    subject: int | str,
    role: str,
    *,
    secret: str | None = None,
    expires_in_seconds: int | None = None,
) -> str:
    """Emite un token de acceso JWT con ``sub``, ``role``, ``iat`` y ``exp``.

    ``secret`` y ``expires_in_seconds`` permiten sobrescribir los valores de
    la configuración, lo que resulta útil en las pruebas.
    """
    clave = settings.jwt_secret if secret is None else secret
    vigencia = (
        settings.access_token_expire_seconds
        if expires_in_seconds is None
        else expires_in_seconds
    )
    emitido_en = int(datetime.now(timezone.utc).timestamp())

    carga_util = {
        "sub": str(subject),
        "role": role,
        "iat": emitido_en,
        "exp": emitido_en + vigencia,
    }
    return jwt.encode(carga_util, clave, algorithm=JWT_ALGORITHM)


def decode_access_token(
    token: str, *, secret: str | None = None
) -> dict[str, Any]:
    """Verifica la firma y la vigencia de un token y devuelve sus ``claims``.

    Lanza ``ExpiredTokenError`` si el token ha caducado e ``InvalidTokenError``
    si la firma no es válida o el token está mal formado.
    """
    clave = settings.jwt_secret if secret is None else secret

    try:
        return jwt.decode(
            token,
            clave,
            algorithms=[JWT_ALGORITHM],
            options={"require_exp": True, "require_sub": True},
        )
    except ExpiredSignatureError as exc:
        raise ExpiredTokenError() from exc
    except JWTError as exc:
        raise InvalidTokenError() from exc
