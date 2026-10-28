"""Pruebas del endpoint público de comprobación de estado."""

from fastapi.testclient import TestClient


def test_el_chequeo_de_salud_responde_ok_sin_cabecera_de_autorizacion(
    cliente: TestClient,
) -> None:
    respuesta = cliente.get("/health")

    assert respuesta.status_code == 200
    assert respuesta.json() == {"status": "ok"}


def test_el_chequeo_de_salud_ignora_un_token_de_portador_invalido(
    cliente: TestClient,
) -> None:
    respuesta = cliente.get(
        "/health",
        headers={"Authorization": "Bearer not-a-valid-token"},
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {"status": "ok"}


def test_el_chequeo_de_salud_devuelve_solo_la_clave_estado(
    cliente: TestClient,
) -> None:
    respuesta = cliente.get("/health")

    assert list(respuesta.json().keys()) == ["status"]
