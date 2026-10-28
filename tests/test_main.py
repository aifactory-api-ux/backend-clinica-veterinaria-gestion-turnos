"""Pruebas del armazón de la aplicación: traducción de los errores de dominio."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.errors import (
    AppointmentConflictError,
    AuthenticationError,
    DomainError,
    PermissionDeniedError,
    ResourceNotFoundError,
)
from app.main import create_app, manejar_error_dominio


def _aplicacion_que_falla(error: DomainError) -> FastAPI:
    """Construye una aplicación mínima cuya única ruta provoca el error dado."""
    aplicacion = FastAPI()
    aplicacion.add_exception_handler(DomainError, manejar_error_dominio)

    @aplicacion.get("/fallo")
    def fallar() -> None:
        raise error

    return aplicacion


@pytest.mark.parametrize(
    ("error", "codigo_esperado"),
    [
        (AuthenticationError(), 401),
        (PermissionDeniedError(), 403),
        (ResourceNotFoundError(), 404),
        (AppointmentConflictError(), 409),
    ],
)
def test_cada_error_de_dominio_se_traduce_a_su_codigo_http(
    error: DomainError, codigo_esperado: int
) -> None:
    with TestClient(_aplicacion_que_falla(error)) as cliente:
        respuesta = cliente.get("/fallo")

    assert respuesta.status_code == codigo_esperado
    assert respuesta.json() == {"detail": error.detail}


def test_los_errores_de_autenticacion_avisan_del_esquema_de_portador() -> None:
    with TestClient(_aplicacion_que_falla(AuthenticationError())) as cliente:
        respuesta = cliente.get("/fallo")

    assert respuesta.headers["WWW-Authenticate"] == "Bearer"


def test_la_aplicacion_registra_el_manejador_de_errores_de_dominio() -> None:
    aplicacion = create_app()

    assert DomainError in aplicacion.exception_handlers
