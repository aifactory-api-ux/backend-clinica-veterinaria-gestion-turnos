"""Pruebas del registro de mascotas de la clínica."""

from collections.abc import Callable
from datetime import date, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.models import Pet
from app.security import create_access_token

# Datos de una mascota válida usados como base de las pruebas.
NOMBRE = "Firulais"
ESPECIE = "dog"
FECHA_NACIMIENTO = "2020-05-10"


def _registrar_mascota(
    cliente: TestClient, cabecera: dict[str, str], **cambios: Any
) -> dict[str, Any]:
    """Registra una mascota y devuelve el cuerpo de la respuesta."""
    cuerpo = {
        "name": NOMBRE,
        "species": ESPECIE,
        "birth_date": FECHA_NACIMIENTO,
    }
    cuerpo.update(cambios)
    respuesta = cliente.post("/pets", json=cuerpo, headers=cabecera)
    assert respuesta.status_code == 201
    datos = respuesta.json()
    assert isinstance(datos, dict)
    return datos


def _numero_de_mascotas(sesion_de_pruebas: sessionmaker[Session]) -> int:
    """Cuenta las mascotas registradas en la base de datos de pruebas."""
    with sesion_de_pruebas() as session:
        return session.query(Pet).count()


def test_el_cliente_registra_una_mascota(
    cliente: TestClient,
    cabecera_cliente: dict[str, str],
    cuenta_cliente: dict[str, Any],
) -> None:
    respuesta = cliente.post(
        "/pets",
        json={"name": NOMBRE, "species": ESPECIE, "birth_date": FECHA_NACIMIENTO},
        headers=cabecera_cliente,
    )

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert set(cuerpo) == {"id", "name", "species", "birth_date", "owner_id"}
    assert cuerpo["id"] > 0
    assert cuerpo["name"] == NOMBRE
    assert cuerpo["species"] == ESPECIE
    assert cuerpo["birth_date"] == FECHA_NACIMIENTO
    assert cuerpo["owner_id"] == cuenta_cliente["id"]


@pytest.mark.parametrize("especie", ["dog", "cat", "other"])
def test_cada_especie_admitida_se_acepta(
    cliente: TestClient, cabecera_cliente: dict[str, str], especie: str
) -> None:
    respuesta = cliente.post(
        "/pets",
        json={"name": NOMBRE, "species": especie, "birth_date": FECHA_NACIMIENTO},
        headers=cabecera_cliente,
    )

    assert respuesta.status_code == 201
    assert respuesta.json()["species"] == especie


def test_el_veterinario_no_puede_registrar_una_mascota(
    cliente: TestClient,
    cabecera_veterinario: dict[str, str],
    sesion_de_pruebas: sessionmaker[Session],
) -> None:
    respuesta = cliente.post(
        "/pets",
        json={"name": NOMBRE, "species": ESPECIE, "birth_date": FECHA_NACIMIENTO},
        headers=cabecera_veterinario,
    )

    assert respuesta.status_code == 403
    cuerpo = respuesta.json()
    assert "id" not in cuerpo
    assert _numero_de_mascotas(sesion_de_pruebas) == 0


def test_una_especie_no_admitida_responde_error_de_validacion(
    cliente: TestClient,
    cabecera_cliente: dict[str, str],
    sesion_de_pruebas: sessionmaker[Session],
) -> None:
    respuesta = cliente.post(
        "/pets",
        json={"name": NOMBRE, "species": "hamster", "birth_date": FECHA_NACIMIENTO},
        headers=cabecera_cliente,
    )

    assert respuesta.status_code == 422
    assert _numero_de_mascotas(sesion_de_pruebas) == 0


def test_una_fecha_de_nacimiento_futura_responde_error_de_validacion(
    cliente: TestClient,
    cabecera_cliente: dict[str, str],
    sesion_de_pruebas: sessionmaker[Session],
) -> None:
    fecha_futura = (date.today() + timedelta(days=365)).isoformat()

    respuesta = cliente.post(
        "/pets",
        json={"name": NOMBRE, "species": ESPECIE, "birth_date": fecha_futura},
        headers=cabecera_cliente,
    )

    assert respuesta.status_code == 422
    assert _numero_de_mascotas(sesion_de_pruebas) == 0


def test_una_fecha_de_nacimiento_lejana_responde_error_de_validacion(
    cliente: TestClient,
    cabecera_cliente: dict[str, str],
    sesion_de_pruebas: sessionmaker[Session],
) -> None:
    respuesta = cliente.post(
        "/pets",
        json={"name": NOMBRE, "species": ESPECIE, "birth_date": "2999-01-01"},
        headers=cabecera_cliente,
    )

    assert respuesta.status_code == 422
    assert _numero_de_mascotas(sesion_de_pruebas) == 0


def test_una_fecha_de_nacimiento_de_hoy_se_acepta(
    cliente: TestClient, cabecera_cliente: dict[str, str]
) -> None:
    respuesta = cliente.post(
        "/pets",
        json={
            "name": NOMBRE,
            "species": ESPECIE,
            "birth_date": date.today().isoformat(),
        },
        headers=cabecera_cliente,
    )

    assert respuesta.status_code == 201
    assert respuesta.json()["birth_date"] == date.today().isoformat()


def test_el_listado_devuelve_solo_las_mascotas_del_cliente(
    cliente: TestClient,
    cabecera_cliente: dict[str, str],
    registrar_cuenta: Callable[[str, str], dict[str, Any]],
) -> None:
    _registrar_mascota(cliente, cabecera_cliente, name="Firulais")
    _registrar_mascota(cliente, cabecera_cliente, name="Michi")

    otro = registrar_cuenta("otro@example.com", "client")
    cabecera_otro = {
        "Authorization": f"Bearer {create_access_token(otro['id'], otro['role'])}"
    }
    _registrar_mascota(cliente, cabecera_otro, name="Rex")

    respuesta = cliente.get("/pets", headers=cabecera_cliente)

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert isinstance(cuerpo, list)
    nombres = [mascota["name"] for mascota in cuerpo]
    assert nombres == ["Firulais", "Michi"]
    assert "Rex" not in nombres


def test_el_listado_de_un_cliente_sin_mascotas_devuelve_un_arreglo_vacio(
    cliente: TestClient, cabecera_cliente: dict[str, str]
) -> None:
    respuesta = cliente.get("/pets", headers=cabecera_cliente)

    assert respuesta.status_code == 200
    assert respuesta.json() == []


def test_el_listado_de_un_veterinario_no_devuelve_mascotas_de_otros(
    cliente: TestClient,
    cabecera_cliente: dict[str, str],
    cabecera_veterinario: dict[str, str],
) -> None:
    _registrar_mascota(cliente, cabecera_cliente, name="Firulais")

    respuesta = cliente.get("/pets", headers=cabecera_veterinario)

    assert respuesta.status_code == 200
    assert respuesta.json() == []


def test_el_registro_sin_token_responde_no_autorizado(cliente: TestClient) -> None:
    respuesta = cliente.post(
        "/pets",
        json={"name": NOMBRE, "species": ESPECIE, "birth_date": FECHA_NACIMIENTO},
    )

    assert respuesta.status_code == 401
    assert respuesta.headers["WWW-Authenticate"] == "Bearer"
    cuerpo = respuesta.json()
    assert "id" not in cuerpo


def test_el_listado_sin_token_responde_no_autorizado(cliente: TestClient) -> None:
    respuesta = cliente.get("/pets")

    assert respuesta.status_code == 401
    assert respuesta.headers["WWW-Authenticate"] == "Bearer"
    cuerpo = respuesta.json()
    assert not isinstance(cuerpo, list)


def test_el_listado_rechaza_un_token_invalido(cliente: TestClient) -> None:
    respuesta = cliente.get("/pets", headers={"Authorization": "Bearer no-es-un-jwt"})

    assert respuesta.status_code == 401
    assert not isinstance(respuesta.json(), list)


def test_el_registro_rechaza_un_token_invalido(cliente: TestClient) -> None:
    respuesta = cliente.post(
        "/pets",
        json={"name": NOMBRE, "species": ESPECIE, "birth_date": FECHA_NACIMIENTO},
        headers={"Authorization": "Bearer no-es-un-jwt"},
    )

    assert respuesta.status_code == 401
    assert "id" not in respuesta.json()
