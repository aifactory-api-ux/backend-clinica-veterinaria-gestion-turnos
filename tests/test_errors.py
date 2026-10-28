"""Pruebas de los errores de dominio y de su equivalencia HTTP."""

import pytest

from app.errors import (
    AppointmentAlreadyCancelledError,
    AppointmentConflictError,
    AuthenticationError,
    ConflictError,
    DomainError,
    DuplicateEmailError,
    InvalidCredentialsError,
    InvalidSlotError,
    PermissionDeniedError,
    ResourceNotFoundError,
)

TODOS_LOS_ERRORES = (
    AuthenticationError,
    InvalidCredentialsError,
    PermissionDeniedError,
    ResourceNotFoundError,
    ConflictError,
    DuplicateEmailError,
    AppointmentConflictError,
    AppointmentAlreadyCancelledError,
    InvalidSlotError,
)


@pytest.mark.parametrize(
    ("error", "codigo_esperado"),
    [
        (AuthenticationError, 401),
        (InvalidCredentialsError, 401),
        (PermissionDeniedError, 403),
        (ResourceNotFoundError, 404),
        (ConflictError, 409),
        (DuplicateEmailError, 409),
        (AppointmentConflictError, 409),
        (AppointmentAlreadyCancelledError, 409),
        (InvalidSlotError, 422),
    ],
)
def test_cada_error_de_dominio_declara_su_codigo_http(
    error: type[DomainError], codigo_esperado: int
) -> None:
    assert error.status_code == codigo_esperado


def test_los_errores_de_dominio_cubren_los_estados_de_la_especificacion() -> None:
    codigos = {error.status_code for error in TODOS_LOS_ERRORES}

    assert {401, 403, 404, 409} <= codigos


def test_el_error_usa_el_mensaje_por_defecto_cuando_no_se_indica_otro() -> None:
    error = DuplicateEmailError()

    assert error.detail == DuplicateEmailError.default_detail
    assert error.to_body() == {"detail": DuplicateEmailError.default_detail}


def test_el_error_acepta_un_mensaje_propio() -> None:
    error = ResourceNotFoundError("No existe la mascota solicitada.")

    assert error.detail == "No existe la mascota solicitada."
    assert error.to_body() == {"detail": "No existe la mascota solicitada."}
