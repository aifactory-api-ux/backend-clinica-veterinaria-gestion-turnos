"""Pruebas de la configuración de la aplicación leída del entorno."""

import pytest

from app.config import (
    DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES,
    DEFAULT_DATABASE_URL,
    DEFAULT_JWT_SECRET,
    Settings,
)

VARIABLES = ("DATABASE_URL", "JWT_SECRET", "ACCESS_TOKEN_EXPIRE_MINUTES")


@pytest.fixture(autouse=True)
def entorno_limpio(monkeypatch: pytest.MonkeyPatch) -> None:
    """Elimina las variables de configuración antes de cada prueba."""
    for variable in VARIABLES:
        monkeypatch.delenv(variable, raising=False)


def test_sin_variables_de_entorno_se_usan_los_valores_por_defecto() -> None:
    settings = Settings.from_env()

    assert settings.database_url == DEFAULT_DATABASE_URL
    assert settings.jwt_secret == DEFAULT_JWT_SECRET
    assert settings.access_token_expire_minutes == DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES


def test_las_variables_de_entorno_sobreescriben_los_valores_por_defecto(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://clinica@db:5432/clinica")
    monkeypatch.setenv("JWT_SECRET", "secreto-de-pruebas")
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15")

    settings = Settings.from_env()

    assert settings.database_url == "postgresql+psycopg://clinica@db:5432/clinica"
    assert settings.jwt_secret == "secreto-de-pruebas"
    assert settings.access_token_expire_minutes == 15
    assert settings.access_token_expire_seconds == 900


def test_una_variable_de_entorno_vacia_se_trata_como_no_definida(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("JWT_SECRET", "   ")

    settings = Settings.from_env()

    assert settings.jwt_secret == DEFAULT_JWT_SECRET


def test_una_duracion_no_numerica_produce_un_error_explicito(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "una-hora")

    with pytest.raises(ValueError):
        Settings.from_env()


def test_una_duracion_no_positiva_produce_un_error_explicito(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "0")

    with pytest.raises(ValueError):
        Settings.from_env()
