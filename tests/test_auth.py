"""Pruebas del registro, el inicio de sesión y la protección con token Bearer."""

from collections.abc import Iterator

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.database import get_db
from app.dependencies import get_current_user
from app.main import create_app
from app.models import User
from app.security import create_access_token, decode_access_token

CONTRASENA = "clinic2024"
EMAIL = "ana@example.com"


@pytest.fixture
def cliente_protegido(
    sesion_de_pruebas: sessionmaker[Session],
) -> Iterator[TestClient]:
    """Cliente HTTP de una aplicación con una ruta protegida por token Bearer.

    La ruta sirve para comprobar el comportamiento de la dependencia de forma
    aislada; los endpoints reales de la clínica tienen además sus propias
    pruebas de protección.
    """
    aplicacion = create_app()

    @aplicacion.get("/ruta-protegida")
    def ruta_protegida(usuario: User = Depends(get_current_user)) -> dict[str, int]:
        return {"id": usuario.id}

    def obtener_sesion() -> Iterator[Session]:
        with sesion_de_pruebas() as session:
            yield session

    aplicacion.dependency_overrides[get_db] = obtener_sesion
    with TestClient(aplicacion) as cliente_http:
        yield cliente_http


def _registrar(
    cliente: TestClient, email: str = EMAIL, role: str = "client"
) -> dict[str, object]:
    """Registra una cuenta y devuelve el cuerpo de la respuesta."""
    respuesta = cliente.post(
        "/auth/register",
        json={"email": email, "password": CONTRASENA, "role": role},
    )
    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert isinstance(cuerpo, dict)
    return cuerpo


def _numero_de_cuentas(sesion_de_pruebas: sessionmaker[Session]) -> int:
    """Cuenta las cuentas registradas en la base de datos de pruebas."""
    with sesion_de_pruebas() as session:
        return session.query(User).count()


def test_el_registro_de_un_cliente_devuelve_sus_datos_publicos(
    cliente: TestClient,
) -> None:
    respuesta = cliente.post(
        "/auth/register",
        json={"email": EMAIL, "password": CONTRASENA, "role": "client"},
    )

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert set(cuerpo) == {"id", "email", "role"}
    assert cuerpo["email"] == EMAIL
    assert cuerpo["role"] == "client"
    assert cuerpo["id"] > 0


def test_el_registro_de_un_veterinario_devuelve_su_rol(cliente: TestClient) -> None:
    respuesta = cliente.post(
        "/auth/register",
        json={"email": "dr.vega@example.com", "password": CONTRASENA, "role": "vet"},
    )

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["email"] == "dr.vega@example.com"
    assert cuerpo["role"] == "vet"


def test_el_registro_no_expone_la_contrasena(cliente: TestClient) -> None:
    respuesta = cliente.post(
        "/auth/register",
        json={"email": EMAIL, "password": CONTRASENA, "role": "client"},
    )

    cuerpo = respuesta.json()
    assert "password" not in cuerpo
    assert "password_hash" not in cuerpo


def test_el_registro_guarda_el_email_normalizado(
    cliente: TestClient, sesion_de_pruebas: sessionmaker[Session]
) -> None:
    respuesta = cliente.post(
        "/auth/register",
        json={"email": "  Ana@Example.COM ", "password": CONTRASENA, "role": "client"},
    )

    assert respuesta.status_code == 201
    assert respuesta.json()["email"] == "ana@example.com"
    with sesion_de_pruebas() as session:
        assert session.query(User).one().email == "ana@example.com"


def test_el_registro_de_un_email_ya_registrado_responde_conflicto(
    cliente: TestClient, sesion_de_pruebas: sessionmaker[Session]
) -> None:
    _registrar(cliente)

    respuesta = cliente.post(
        "/auth/register",
        json={"email": EMAIL, "password": CONTRASENA, "role": "client"},
    )

    assert respuesta.status_code == 409
    cuerpo = respuesta.json()
    assert "id" not in cuerpo
    assert "email" not in cuerpo
    assert "role" not in cuerpo
    assert _numero_de_cuentas(sesion_de_pruebas) == 1


def test_el_registro_rechaza_un_email_duplicado_con_otra_mayuscula(
    cliente: TestClient, sesion_de_pruebas: sessionmaker[Session]
) -> None:
    _registrar(cliente)

    respuesta = cliente.post(
        "/auth/register",
        json={"email": "ANA@example.com", "password": CONTRASENA, "role": "vet"},
    )

    assert respuesta.status_code == 409
    assert _numero_de_cuentas(sesion_de_pruebas) == 1


def test_el_registro_con_una_contrasena_corta_responde_error_de_validacion(
    cliente: TestClient, sesion_de_pruebas: sessionmaker[Session]
) -> None:
    respuesta = cliente.post(
        "/auth/register",
        json={"email": EMAIL, "password": "abc1234", "role": "client"},
    )

    assert respuesta.status_code == 422
    assert _numero_de_cuentas(sesion_de_pruebas) == 0


def test_el_registro_con_un_rol_desconocido_responde_error_de_validacion(
    cliente: TestClient, sesion_de_pruebas: sessionmaker[Session]
) -> None:
    respuesta = cliente.post(
        "/auth/register",
        json={"email": EMAIL, "password": CONTRASENA, "role": "admin"},
    )

    assert respuesta.status_code == 422
    assert _numero_de_cuentas(sesion_de_pruebas) == 0


def test_el_registro_sin_rol_responde_error_de_validacion(
    cliente: TestClient,
) -> None:
    respuesta = cliente.post(
        "/auth/register",
        json={"email": EMAIL, "password": CONTRASENA},
    )

    assert respuesta.status_code == 422


def test_el_inicio_de_sesion_devuelve_un_token_de_portador(cliente: TestClient) -> None:
    cuenta = _registrar(cliente)

    respuesta = cliente.post(
        "/auth/login", json={"email": EMAIL, "password": CONTRASENA}
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert set(cuerpo) == {"access_token", "token_type"}
    assert cuerpo["token_type"] == "bearer"

    token = cuerpo["access_token"]
    assert token.count(".") == 2
    claims = decode_access_token(token)
    assert claims["sub"] == str(cuenta["id"])
    assert claims["role"] == "client"


def test_el_inicio_de_sesion_con_una_contrasena_incorrecta_responde_401(
    cliente: TestClient,
) -> None:
    _registrar(cliente)

    respuesta = cliente.post(
        "/auth/login", json={"email": EMAIL, "password": "contrasena-mala"}
    )

    assert respuesta.status_code == 401
    assert "access_token" not in respuesta.json()


def test_el_inicio_de_sesion_con_un_email_desconocido_responde_401(
    cliente: TestClient,
) -> None:
    respuesta = cliente.post(
        "/auth/login",
        json={"email": "nobody@example.com", "password": CONTRASENA},
    )

    assert respuesta.status_code == 401
    assert "access_token" not in respuesta.json()


def test_los_credenciales_incorrectos_no_revelan_que_cuentas_existen(
    cliente: TestClient,
) -> None:
    _registrar(cliente)

    con_contrasena_mala = cliente.post(
        "/auth/login", json={"email": EMAIL, "password": "contrasena-mala"}
    )
    con_email_desconocido = cliente.post(
        "/auth/login",
        json={"email": "nobody@example.com", "password": CONTRASENA},
    )

    assert con_contrasena_mala.json() == con_email_desconocido.json()


def test_una_ruta_protegida_exige_la_cabecera_de_autorizacion(
    cliente_protegido: TestClient,
) -> None:
    respuesta = cliente_protegido.get("/ruta-protegida")

    assert respuesta.status_code == 401
    assert respuesta.headers["WWW-Authenticate"] == "Bearer"


def test_una_ruta_protegida_rechaza_un_token_mal_formado(
    cliente_protegido: TestClient,
) -> None:
    respuesta = cliente_protegido.get(
        "/ruta-protegida", headers={"Authorization": "Bearer not-a-jwt"}
    )

    assert respuesta.status_code == 401


def test_una_ruta_protegida_rechaza_un_esquema_distinto_de_portador(
    cliente_protegido: TestClient,
) -> None:
    respuesta = cliente_protegido.get(
        "/ruta-protegida", headers={"Authorization": "Basic dXNlcjpwYXNz"}
    )

    assert respuesta.status_code == 401


def test_una_ruta_protegida_rechaza_un_token_firmado_con_otra_clave(
    cliente_protegido: TestClient,
) -> None:
    token = create_access_token(1, "client", secret="otra-clave")

    respuesta = cliente_protegido.get(
        "/ruta-protegida", headers={"Authorization": f"Bearer {token}"}
    )

    assert respuesta.status_code == 401


def test_una_ruta_protegida_rechaza_un_token_caducado(
    cliente_protegido: TestClient,
) -> None:
    token = create_access_token(1, "client", expires_in_seconds=-60)

    respuesta = cliente_protegido.get(
        "/ruta-protegida", headers={"Authorization": f"Bearer {token}"}
    )

    assert respuesta.status_code == 401


def test_una_ruta_protegida_rechaza_un_token_de_una_cuenta_inexistente(
    cliente_protegido: TestClient,
) -> None:
    token = create_access_token(999, "client")

    respuesta = cliente_protegido.get(
        "/ruta-protegida", headers={"Authorization": f"Bearer {token}"}
    )

    assert respuesta.status_code == 401


def test_una_ruta_protegida_acepta_el_token_de_una_cuenta_registrada(
    cliente: TestClient, cliente_protegido: TestClient
) -> None:
    cuenta = _registrar(cliente)
    token = create_access_token(cuenta["id"], cuenta["role"])

    respuesta = cliente_protegido.get(
        "/ruta-protegida", headers={"Authorization": f"Bearer {token}"}
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {"id": cuenta["id"]}


def test_el_token_emitido_en_el_inicio_de_sesion_abre_una_ruta_protegida(
    cliente: TestClient, cliente_protegido: TestClient
) -> None:
    _registrar(cliente)
    inicio = cliente.post(
        "/auth/login", json={"email": EMAIL, "password": CONTRASENA}
    )
    token = inicio.json()["access_token"]

    respuesta = cliente_protegido.get(
        "/ruta-protegida", headers={"Authorization": f"Bearer {token}"}
    )

    assert respuesta.status_code == 200


def test_el_listado_de_mascotas_rechaza_un_token_caducado(cliente: TestClient) -> None:
    token = create_access_token(1, "client", expires_in_seconds=-60)

    respuesta = cliente.get("/pets", headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 401
    assert not isinstance(respuesta.json(), list)


def test_el_listado_de_turnos_rechaza_un_token_firmado_con_otra_clave(
    cliente: TestClient,
) -> None:
    token = create_access_token(1, "client", secret="otra-clave")

    respuesta = cliente.get("/appointments", headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 401
    assert not isinstance(respuesta.json(), list)
