"""Configuración de la aplicación, resuelta desde las variables de entorno."""

import os
from dataclasses import dataclass

# Valores por defecto orientados al desarrollo local sin servidor de datos.
DEFAULT_DATABASE_URL = "sqlite:///./clinica.db"
DEFAULT_JWT_SECRET = "dev-secret-change-me"
DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Algoritmo de firma de los tokens JWT emitidos por la API.
JWT_ALGORITHM = "HS256"


def _read_text(name: str, default: str) -> str:
    """Devuelve la variable de entorno indicada o el valor por defecto."""
    value = os.environ.get(name, "").strip()
    return value or default


def _read_positive_int(name: str, default: int) -> int:
    """Devuelve la variable de entorno indicada como entero positivo."""
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(
            f"La variable de entorno {name} debe ser un entero, recibido: {raw!r}"
        ) from exc
    if value <= 0:
        raise ValueError(f"La variable de entorno {name} debe ser mayor que cero: {value}")
    return value


@dataclass(frozen=True)
class Settings:
    """Ajustes de ejecución de la API."""

    database_url: str = DEFAULT_DATABASE_URL
    jwt_secret: str = DEFAULT_JWT_SECRET
    access_token_expire_minutes: int = DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES

    @classmethod
    def from_env(cls) -> "Settings":
        """Construye los ajustes a partir del entorno actual."""
        return cls(
            database_url=_read_text("DATABASE_URL", DEFAULT_DATABASE_URL),
            jwt_secret=_read_text("JWT_SECRET", DEFAULT_JWT_SECRET),
            access_token_expire_minutes=_read_positive_int(
                "ACCESS_TOKEN_EXPIRE_MINUTES", DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES
            ),
        )

    @property
    def access_token_expire_seconds(self) -> int:
        """Duración del token de acceso expresada en segundos."""
        return self.access_token_expire_minutes * 60


settings = Settings.from_env()
