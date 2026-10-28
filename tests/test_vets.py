"""Pruebas del directorio de veterinarios de la clínica."""

from collections.abc import Callable
from typing import Any

from fastapi.testclient import TestClient


def test_el_directorio_devuelve_200_con_un_arreglo(
    cliente: TestClient, cabecera_cliente: dict[str, str]
) -> None:
    respuesta = cliente.get("/vets", headers=cabecera_cliente)

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert isinstance(cuerpo, list)


def test_cada_veterinario_del_directorio_expone_solo_id_y_email(
    cliente: TestClient,
    cabecera_cliente: dict[str, str],
    registrar_cuenta: Callable[[str, str], dict[str, Any]],
) -> None:
    registrar_cuenta("dr.vega@example.com", "vet")
    registrar_cuenta("dr.paz@example.com", "vet")

    respuesta = cliente.get("/vets", headers=cabecera_cliente)

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert len(cuerpo) == 2
    for veterinario in cuerpo:
        assert set(veterinario) == {"id", "email"}
        assert isinstance(veterinario["id"], int)
        assert isinstance(veterinario["email"], str)


def test_el_directorio_incluye_a_los_veterinarios(
    cliente: TestClient,
    cabecera_cliente: dict[str, str],
    cuenta_veterinario: dict[str, Any],
) -> None:
    respuesta = cliente.get("/vets", headers=cabecera_cliente)

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    esperado = {
        "id": cuenta_veterinario["id"],
        "email": cuenta_veterinario["email"],
    }
    assert esperado in cuerpo


def test_el_directorio_no_incluye_a_los_clientes(
    cliente: TestClient,
    cabecera_cliente: dict[str, str],
    cuenta_cliente: dict[str, Any],
) -> None:
    respuesta = cliente.get("/vets", headers=cabecera_cliente)

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuenta_cliente["email"] not in [v["email"] for v in cuerpo]


def test_el_directorio_acepta_el_token_de_un_veterinario(
    cliente: TestClient, cabecera_veterinario: dict[str, str]
) -> None:
    respuesta = cliente.get("/vets", headers=cabecera_veterinario)

    assert respuesta.status_code == 200
    assert isinstance(respuesta.json(), list)


def test_el_directorio_sin_veterinarios_devuelve_un_arreglo_vacio(
    cliente: TestClient, cabecera_cliente: dict[str, str]
) -> None:
    respuesta = cliente.get("/vets", headers=cabecera_cliente)

    assert respuesta.status_code == 200
    assert respuesta.json() == []


def test_el_directorio_exige_la_cabecera_de_autorizacion(
    cliente: TestClient,
) -> None:
    respuesta = cliente.get("/vets")

    assert respuesta.status_code == 401
    assert respuesta.headers["WWW-Authenticate"] == "Bearer"
    cuerpo = respuesta.json()
    assert not isinstance(cuerpo, list)
    assert "email" not in cuerpo


def test_el_directorio_rechaza_un_token_invalido(cliente: TestClient) -> None:
    respuesta = cliente.get("/vets", headers={"Authorization": "Bearer no-es-un-jwt"})

    assert respuesta.status_code == 401
    assert not isinstance(respuesta.json(), list)
