"""Infraestructura común de las pruebas: base de datos aislada y cliente HTTP."""

import os
from collections.abc import Callable, Iterator
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# La aplicación toma la URL de la base de datos del entorno al importarse; en
# las pruebas se usa una base en memoria para no dejar ficheros en el repositorio.
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from app.database import Base, get_db  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models import Appointment, Pet, User  # noqa: E402
from app.security import create_access_token  # noqa: E402

# Credenciales usadas por las cuentas que registran las pruebas.
CONTRASENA_PRUEBAS = "clinic2024"
EMAIL_CLIENTE = "ana@example.com"
EMAIL_VETERINARIO = "dr.vega@example.com"

# Días de la semana según la numeración de ``datetime.weekday()``.
LUNES = 0
DOMINGO = 6


def instante_futuro(dia_semana: int, hora: int, minuto: int = 0) -> datetime:
    """Devuelve el próximo instante UTC que cae en el día de la semana dado.

    El instante devuelto es siempre posterior al momento actual, de modo que
    las pruebas no dependan de fechas concretas ni caduquen con el tiempo.
    """
    ahora = datetime.now(timezone.utc)
    dias = (dia_semana - ahora.weekday()) % 7
    candidato = ahora.replace(
        hour=hora, minute=minuto, second=0, microsecond=0
    ) + timedelta(days=dias)
    if candidato <= ahora:
        candidato += timedelta(days=7)
    return candidato


@pytest.fixture(scope="session")
def motor_de_pruebas() -> Iterator[Engine]:
    """Motor SQLite en memoria con una única conexión compartida."""
    motor = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(motor)
    try:
        yield motor
    finally:
        motor.dispose()


@pytest.fixture(scope="session")
def sesion_de_pruebas(motor_de_pruebas: Engine) -> sessionmaker[Session]:
    """Factoría de sesiones ligada al motor de pruebas."""
    return sessionmaker(
        bind=motor_de_pruebas,
        autoflush=False,
        expire_on_commit=False,
    )


@pytest.fixture(scope="session")
def aplicacion(sesion_de_pruebas: sessionmaker[Session]) -> FastAPI:
    """Aplicación configurada para usar la base de datos de pruebas."""

    def obtener_sesion() -> Iterator[Session]:
        with sesion_de_pruebas() as session:
            yield session

    aplicacion_de_pruebas = create_app()
    aplicacion_de_pruebas.dependency_overrides[get_db] = obtener_sesion
    return aplicacion_de_pruebas


@pytest.fixture
def cliente(aplicacion: FastAPI) -> Iterator[TestClient]:
    """Cliente HTTP con el ciclo de vida de la aplicación en marcha."""
    with TestClient(aplicacion) as cliente_http:
        yield cliente_http


@pytest.fixture(autouse=True)
def limpiar_datos(sesion_de_pruebas: sessionmaker[Session]) -> Iterator[None]:
    """Deja la base de datos de pruebas sin filas antes de cada prueba."""
    with sesion_de_pruebas() as session:
        for modelo in (Appointment, Pet, User):
            session.query(modelo).delete()
        session.commit()
    yield


@pytest.fixture
def registrar_cuenta(
    cliente: TestClient,
) -> Callable[[str, str], dict[str, Any]]:
    """Devuelve una función que registra una cuenta y devuelve sus datos.

    Las cuentas se dan de alta por la API pública, de modo que las pruebas
    usan el mismo camino que usaría el equipo de la clínica.
    """

    def registrar(email: str, role: str = "client") -> dict[str, Any]:
        respuesta = cliente.post(
            "/auth/register",
            json={"email": email, "password": CONTRASENA_PRUEBAS, "role": role},
        )
        assert respuesta.status_code == 201
        return respuesta.json()

    return registrar


@pytest.fixture
def cuenta_cliente(
    registrar_cuenta: Callable[[str, str], dict[str, Any]],
) -> dict[str, Any]:
    """Cuenta de cliente registrada en la base de datos de pruebas."""
    return registrar_cuenta(EMAIL_CLIENTE, "client")


@pytest.fixture
def cuenta_veterinario(
    registrar_cuenta: Callable[[str, str], dict[str, Any]],
) -> dict[str, Any]:
    """Cuenta de veterinario registrada en la base de datos de pruebas."""
    return registrar_cuenta(EMAIL_VETERINARIO, "vet")


def cabecera_bearer(cuenta: dict[str, Any]) -> dict[str, str]:
    """Construye la cabecera ``Authorization`` de una cuenta registrada."""
    token = create_access_token(cuenta["id"], cuenta["role"])
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def cabecera_cliente(cuenta_cliente: dict[str, Any]) -> dict[str, str]:
    """Cabecera ``Authorization`` de la cuenta de cliente."""
    return cabecera_bearer(cuenta_cliente)


@pytest.fixture
def cabecera_veterinario(cuenta_veterinario: dict[str, Any]) -> dict[str, str]:
    """Cabecera ``Authorization`` de la cuenta de veterinario."""
    return cabecera_bearer(cuenta_veterinario)
