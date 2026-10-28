"""Pruebas de la gestión de turnos de la clínica.

Cubre la creación de un turno (reglas de franja horaria, propiedad de la
mascota, existencia de la mascota y del veterinario y conflictos de agenda),
el listado de turnos según el rol del usuario autenticado y la cancelación de
un turno por su dueño o por su veterinario.
"""

from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.models import Appointment
from app.security import create_access_token
from tests.conftest import DOMINGO, LUNES, cabecera_bearer, instante_futuro

# Datos de una mascota válida usados como base de las pruebas.
NOMBRE = "Firulais"
ESPECIE = "dog"
FECHA_NACIMIENTO = "2020-05-10"

# Estado de un turno activo.
ESTADO_PROGRAMADO = "scheduled"

# Estado de un turno cancelado.
ESTADO_CANCELADO = "cancelled"


def _registrar_mascota(
    cliente: TestClient, cabecera: dict[str, str], nombre: str = NOMBRE
) -> dict[str, Any]:
    """Registra una mascota y devuelve sus datos."""
    respuesta = cliente.post(
        "/pets",
        json={"name": nombre, "species": ESPECIE, "birth_date": FECHA_NACIMIENTO},
        headers=cabecera,
    )
    assert respuesta.status_code == 201
    datos = respuesta.json()
    assert isinstance(datos, dict)
    return datos


def _iso_utc(instante: datetime) -> str:
    """Devuelve el instante en ISO 8601 con el designador de zona UTC."""
    return instante.isoformat().replace("+00:00", "Z")


def _numero_de_turnos(sesion_de_pruebas: sessionmaker[Session]) -> int:
    """Cuenta los turnos registrados en la base de datos de pruebas."""
    with sesion_de_pruebas() as session:
        return session.query(Appointment).count()


def _agendar_turno(
    cliente: TestClient,
    cabecera: dict[str, str],
    *,
    pet_id: int,
    vet_id: int,
    inicio: datetime,
) -> dict[str, Any]:
    """Agenda un turno y devuelve sus datos."""
    respuesta = cliente.post(
        "/appointments",
        json={"pet_id": pet_id, "vet_id": vet_id, "start_at": _iso_utc(inicio)},
        headers=cabecera,
    )
    assert respuesta.status_code == 201
    datos = respuesta.json()
    assert isinstance(datos, dict)
    return datos


def _estado_del_turno(
    sesion_de_pruebas: sessionmaker[Session], turno_id: int
) -> str:
    """Devuelve el estado persistido de un turno."""
    with sesion_de_pruebas() as session:
        turno = session.get(Appointment, turno_id)
        assert turno is not None
        return turno.status


def test_el_cliente_agenda_un_turno(
    cliente: TestClient,
    cabecera_cliente: dict[str, str],
    cabecera_veterinario: dict[str, str],
    cuenta_veterinario: dict[str, Any],
) -> None:
    mascota = _registrar_mascota(cliente, cabecera_cliente)
    inicio = instante_futuro(LUNES, 10)

    respuesta = cliente.post(
        "/appointments",
        json={
            "pet_id": mascota["id"],
            "vet_id": cuenta_veterinario["id"],
            "start_at": _iso_utc(inicio),
        },
        headers=cabecera_cliente,
    )

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert set(cuerpo) == {"id", "pet_id", "vet_id", "start_at", "end_at", "status"}
    assert cuerpo["id"] > 0
    assert cuerpo["pet_id"] == mascota["id"]
    assert cuerpo["vet_id"] == cuenta_veterinario["id"]
    assert cuerpo["start_at"] == _iso_utc(inicio)
    assert cuerpo["status"] == "scheduled"


def test_el_turno_dura_treinta_minutos(
    cliente: TestClient,
    cabecera_cliente: dict[str, str],
    cuenta_veterinario: dict[str, Any],
) -> None:
    mascota = _registrar_mascota(cliente, cabecera_cliente)
    inicio = instante_futuro(LUNES, 10)

    respuesta = cliente.post(
        "/appointments",
        json={
            "pet_id": mascota["id"],
            "vet_id": cuenta_veterinario["id"],
            "start_at": _iso_utc(inicio),
        },
        headers=cabecera_cliente,
    )

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    fin = datetime.fromisoformat(cuerpo["end_at"])
    assert fin - datetime.fromisoformat(cuerpo["start_at"]) == timedelta(minutes=30)


def test_un_veterinario_no_puede_agendar_un_turno(
    cliente: TestClient,
    cabecera_veterinario: dict[str, str],
    cuenta_veterinario: dict[str, Any],
    sesion_de_pruebas: sessionmaker[Session],
) -> None:
    respuesta = cliente.post(
        "/appointments",
        json={
            "pet_id": 1,
            "vet_id": cuenta_veterinario["id"],
            "start_at": _iso_utc(instante_futuro(LUNES, 10)),
        },
        headers=cabecera_veterinario,
    )

    assert respuesta.status_code == 403
    cuerpo = respuesta.json()
    assert "id" not in cuerpo
    assert _numero_de_turnos(sesion_de_pruebas) == 0


def test_no_se_agenda_un_turno_para_una_mascota_ajena(
    cliente: TestClient,
    cabecera_cliente: dict[str, str],
    registrar_cuenta: Callable[[str, str], dict[str, Any]],
    cuenta_veterinario: dict[str, Any],
    sesion_de_pruebas: sessionmaker[Session],
) -> None:
    mascota = _registrar_mascota(cliente, cabecera_cliente)

    otro = registrar_cuenta("otro@example.com", "client")
    cabecera_otro = {
        "Authorization": f"Bearer {create_access_token(otro['id'], otro['role'])}"
    }

    respuesta = cliente.post(
        "/appointments",
        json={
            "pet_id": mascota["id"],
            "vet_id": cuenta_veterinario["id"],
            "start_at": _iso_utc(instante_futuro(LUNES, 10)),
        },
        headers=cabecera_otro,
    )

    assert respuesta.status_code == 403
    assert "id" not in respuesta.json()
    assert _numero_de_turnos(sesion_de_pruebas) == 0


def test_una_mascota_inexistente_responde_no_encontrado(
    cliente: TestClient,
    cabecera_cliente: dict[str, str],
    cuenta_veterinario: dict[str, Any],
    sesion_de_pruebas: sessionmaker[Session],
) -> None:
    respuesta = cliente.post(
        "/appointments",
        json={
            "pet_id": 999999,
            "vet_id": cuenta_veterinario["id"],
            "start_at": _iso_utc(instante_futuro(LUNES, 10)),
        },
        headers=cabecera_cliente,
    )

    assert respuesta.status_code == 404
    assert "id" not in respuesta.json()
    assert _numero_de_turnos(sesion_de_pruebas) == 0


def test_un_veterinario_inexistente_responde_no_encontrado(
    cliente: TestClient,
    cabecera_cliente: dict[str, str],
    sesion_de_pruebas: sessionmaker[Session],
) -> None:
    mascota = _registrar_mascota(cliente, cabecera_cliente)

    respuesta = cliente.post(
        "/appointments",
        json={
            "pet_id": mascota["id"],
            "vet_id": 999999,
            "start_at": _iso_utc(instante_futuro(LUNES, 10)),
        },
        headers=cabecera_cliente,
    )

    assert respuesta.status_code == 404
    assert "id" not in respuesta.json()
    assert _numero_de_turnos(sesion_de_pruebas) == 0


def test_un_horario_ya_ocupado_responde_conflicto(
    cliente: TestClient,
    cabecera_cliente: dict[str, str],
    cuenta_veterinario: dict[str, Any],
    sesion_de_pruebas: sessionmaker[Session],
) -> None:
    mascota = _registrar_mascota(cliente, cabecera_cliente)
    inicio = _iso_utc(instante_futuro(LUNES, 10))
    cuerpo = {
        "pet_id": mascota["id"],
        "vet_id": cuenta_veterinario["id"],
        "start_at": inicio,
    }

    primera = cliente.post("/appointments", json=cuerpo, headers=cabecera_cliente)
    segunda = cliente.post("/appointments", json=cuerpo, headers=cabecera_cliente)

    assert primera.status_code == 201
    assert segunda.status_code == 409
    assert "id" not in segunda.json()
    assert _numero_de_turnos(sesion_de_pruebas) == 1


def test_el_ultimo_inicio_del_dia_se_acepta(
    cliente: TestClient,
    cabecera_cliente: dict[str, str],
    cuenta_veterinario: dict[str, Any],
) -> None:
    mascota = _registrar_mascota(cliente, cabecera_cliente)
    inicio = instante_futuro(LUNES, 17, 30)

    respuesta = cliente.post(
        "/appointments",
        json={
            "pet_id": mascota["id"],
            "vet_id": cuenta_veterinario["id"],
            "start_at": _iso_utc(inicio),
        },
        headers=cabecera_cliente,
    )

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["start_at"] == _iso_utc(inicio)
    fin = datetime.fromisoformat(cuerpo["end_at"])
    assert (fin.hour, fin.minute) == (18, 0)


def test_un_domingo_responde_error_de_validacion(
    cliente: TestClient,
    cabecera_cliente: dict[str, str],
    cuenta_veterinario: dict[str, Any],
    sesion_de_pruebas: sessionmaker[Session],
) -> None:
    mascota = _registrar_mascota(cliente, cabecera_cliente)

    respuesta = cliente.post(
        "/appointments",
        json={
            "pet_id": mascota["id"],
            "vet_id": cuenta_veterinario["id"],
            "start_at": _iso_utc(instante_futuro(DOMINGO, 10)),
        },
        headers=cabecera_cliente,
    )

    assert respuesta.status_code == 422
    assert _numero_de_turnos(sesion_de_pruebas) == 0


def test_una_hora_con_minutos_no_admitidos_responde_error_de_validacion(
    cliente: TestClient,
    cabecera_cliente: dict[str, str],
    cuenta_veterinario: dict[str, Any],
    sesion_de_pruebas: sessionmaker[Session],
) -> None:
    mascota = _registrar_mascota(cliente, cabecera_cliente)

    respuesta = cliente.post(
        "/appointments",
        json={
            "pet_id": mascota["id"],
            "vet_id": cuenta_veterinario["id"],
            "start_at": _iso_utc(instante_futuro(LUNES, 10, 15)),
        },
        headers=cabecera_cliente,
    )

    assert respuesta.status_code == 422
    assert _numero_de_turnos(sesion_de_pruebas) == 0


def test_un_inicio_en_el_pasado_responde_error_de_validacion(
    cliente: TestClient,
    cabecera_cliente: dict[str, str],
    cuenta_veterinario: dict[str, Any],
    sesion_de_pruebas: sessionmaker[Session],
) -> None:
    mascota = _registrar_mascota(cliente, cabecera_cliente)
    pasado = datetime.now(timezone.utc) - timedelta(days=1)

    respuesta = cliente.post(
        "/appointments",
        json={
            "pet_id": mascota["id"],
            "vet_id": cuenta_veterinario["id"],
            "start_at": _iso_utc(pasado),
        },
        headers=cabecera_cliente,
    )

    assert respuesta.status_code == 422
    assert _numero_de_turnos(sesion_de_pruebas) == 0


def test_un_inicio_sin_zona_horaria_responde_error_de_validacion(
    cliente: TestClient,
    cabecera_cliente: dict[str, str],
    cuenta_veterinario: dict[str, Any],
) -> None:
    mascota = _registrar_mascota(cliente, cabecera_cliente)

    respuesta = cliente.post(
        "/appointments",
        json={
            "pet_id": mascota["id"],
            "vet_id": cuenta_veterinario["id"],
            "start_at": instante_futuro(LUNES, 10).replace(tzinfo=None).isoformat(),
        },
        headers=cabecera_cliente,
    )

    assert respuesta.status_code == 422


def test_el_registro_de_turnos_sin_token_responde_no_autorizado(
    cliente: TestClient,
) -> None:
    respuesta = cliente.post(
        "/appointments",
        json={
            "pet_id": 1,
            "vet_id": 2,
            "start_at": _iso_utc(instante_futuro(LUNES, 10)),
        },
    )

    assert respuesta.status_code == 401
    assert respuesta.headers["WWW-Authenticate"] == "Bearer"
    assert "id" not in respuesta.json()


def test_el_cliente_ve_solo_los_turnos_de_sus_mascotas(
    cliente: TestClient,
    cabecera_cliente: dict[str, str],
    cuenta_veterinario: dict[str, Any],
    registrar_cuenta: Callable[[str, str], dict[str, Any]],
) -> None:
    mascota_propia = _registrar_mascota(cliente, cabecera_cliente)

    otro_cliente = registrar_cuenta("otro@example.com", "client")
    cabecera_otro_cliente = cabecera_bearer(otro_cliente)
    mascota_ajena = _registrar_mascota(
        cliente, cabecera_otro_cliente, nombre="Michi"
    )

    otro_veterinario = registrar_cuenta("dr.otro@example.com", "vet")

    turno_propio = _agendar_turno(
        cliente,
        cabecera_cliente,
        pet_id=mascota_propia["id"],
        vet_id=cuenta_veterinario["id"],
        inicio=instante_futuro(LUNES, 10),
    )
    turno_propio_de_otro_vet = _agendar_turno(
        cliente,
        cabecera_cliente,
        pet_id=mascota_propia["id"],
        vet_id=otro_veterinario["id"],
        inicio=instante_futuro(LUNES, 11),
    )
    turno_ajeno = _agendar_turno(
        cliente,
        cabecera_otro_cliente,
        pet_id=mascota_ajena["id"],
        vet_id=cuenta_veterinario["id"],
        inicio=instante_futuro(LUNES, 12),
    )

    respuesta = cliente.get("/appointments", headers=cabecera_cliente)

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert isinstance(cuerpo, list)
    identificadores = {turno["id"] for turno in cuerpo}
    assert identificadores == {turno_propio["id"], turno_propio_de_otro_vet["id"]}
    assert turno_ajeno["id"] not in identificadores


def test_el_veterinario_ve_solo_sus_propios_turnos(
    cliente: TestClient,
    cabecera_cliente: dict[str, str],
    cabecera_veterinario: dict[str, str],
    cuenta_veterinario: dict[str, Any],
    registrar_cuenta: Callable[[str, str], dict[str, Any]],
) -> None:
    mascota = _registrar_mascota(cliente, cabecera_cliente)

    otro_veterinario = registrar_cuenta("dr.otro@example.com", "vet")
    cabecera_otro_veterinario = cabecera_bearer(otro_veterinario)

    turno_propio = _agendar_turno(
        cliente,
        cabecera_cliente,
        pet_id=mascota["id"],
        vet_id=cuenta_veterinario["id"],
        inicio=instante_futuro(LUNES, 10),
    )
    turno_de_otro_vet = _agendar_turno(
        cliente,
        cabecera_cliente,
        pet_id=mascota["id"],
        vet_id=otro_veterinario["id"],
        inicio=instante_futuro(LUNES, 11),
    )

    respuesta = cliente.get("/appointments", headers=cabecera_veterinario)

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert isinstance(cuerpo, list)
    identificadores = {turno["id"] for turno in cuerpo}
    assert identificadores == {turno_propio["id"]}
    assert turno_de_otro_vet["id"] not in identificadores

    respuesta_otro = cliente.get("/appointments", headers=cabecera_otro_veterinario)

    assert respuesta_otro.status_code == 200
    cuerpo_otro = respuesta_otro.json()
    assert isinstance(cuerpo_otro, list)
    assert {turno["id"] for turno in cuerpo_otro} == {turno_de_otro_vet["id"]}


def test_el_listado_de_turnos_sin_token_responde_no_autorizado(
    cliente: TestClient,
) -> None:
    respuesta = cliente.get("/appointments")

    assert respuesta.status_code == 401
    assert respuesta.headers["WWW-Authenticate"] == "Bearer"
    assert not isinstance(respuesta.json(), list)


def test_el_dueno_de_la_mascota_cancela_su_turno(
    cliente: TestClient,
    cabecera_cliente: dict[str, str],
    cuenta_veterinario: dict[str, Any],
    sesion_de_pruebas: sessionmaker[Session],
) -> None:
    mascota = _registrar_mascota(cliente, cabecera_cliente)
    turno = _agendar_turno(
        cliente,
        cabecera_cliente,
        pet_id=mascota["id"],
        vet_id=cuenta_veterinario["id"],
        inicio=instante_futuro(LUNES, 10),
    )

    respuesta = cliente.post(
        f"/appointments/{turno['id']}/cancel", headers=cabecera_cliente
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["id"] == turno["id"]
    assert cuerpo["status"] == ESTADO_CANCELADO
    assert _estado_del_turno(sesion_de_pruebas, turno["id"]) == ESTADO_CANCELADO


def test_el_veterinario_cancela_su_turno(
    cliente: TestClient,
    cabecera_cliente: dict[str, str],
    cabecera_veterinario: dict[str, str],
    cuenta_veterinario: dict[str, Any],
    sesion_de_pruebas: sessionmaker[Session],
) -> None:
    mascota = _registrar_mascota(cliente, cabecera_cliente)
    turno = _agendar_turno(
        cliente,
        cabecera_cliente,
        pet_id=mascota["id"],
        vet_id=cuenta_veterinario["id"],
        inicio=instante_futuro(LUNES, 10),
    )

    respuesta = cliente.post(
        f"/appointments/{turno['id']}/cancel", headers=cabecera_veterinario
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["id"] == turno["id"]
    assert cuerpo["status"] == ESTADO_CANCELADO
    assert _estado_del_turno(sesion_de_pruebas, turno["id"]) == ESTADO_CANCELADO


def test_un_usuario_no_relacionado_no_puede_cancelar_el_turno(
    cliente: TestClient,
    cabecera_cliente: dict[str, str],
    cuenta_veterinario: dict[str, Any],
    registrar_cuenta: Callable[[str, str], dict[str, Any]],
    sesion_de_pruebas: sessionmaker[Session],
) -> None:
    mascota = _registrar_mascota(cliente, cabecera_cliente)
    turno = _agendar_turno(
        cliente,
        cabecera_cliente,
        pet_id=mascota["id"],
        vet_id=cuenta_veterinario["id"],
        inicio=instante_futuro(LUNES, 10),
    )

    otro_cliente = registrar_cuenta("otro@example.com", "client")
    otro_veterinario = registrar_cuenta("dr.otro@example.com", "vet")

    for cuenta in (otro_cliente, otro_veterinario):
        respuesta = cliente.post(
            f"/appointments/{turno['id']}/cancel", headers=cabecera_bearer(cuenta)
        )

        assert respuesta.status_code == 403
        assert respuesta.json().get("status") != ESTADO_CANCELADO

    assert _estado_del_turno(sesion_de_pruebas, turno["id"]) == ESTADO_PROGRAMADO


def test_cancelar_un_turno_inexistente_responde_no_encontrado(
    cliente: TestClient,
    cabecera_cliente: dict[str, str],
) -> None:
    respuesta = cliente.post(
        "/appointments/999999/cancel", headers=cabecera_cliente
    )

    assert respuesta.status_code == 404
    assert respuesta.json().get("status") != ESTADO_CANCELADO


def test_cancelar_un_turno_ya_cancelado_responde_conflicto(
    cliente: TestClient,
    cabecera_cliente: dict[str, str],
    cuenta_veterinario: dict[str, Any],
) -> None:
    mascota = _registrar_mascota(cliente, cabecera_cliente)
    turno = _agendar_turno(
        cliente,
        cabecera_cliente,
        pet_id=mascota["id"],
        vet_id=cuenta_veterinario["id"],
        inicio=instante_futuro(LUNES, 10),
    )

    primera = cliente.post(
        f"/appointments/{turno['id']}/cancel", headers=cabecera_cliente
    )
    segunda = cliente.post(
        f"/appointments/{turno['id']}/cancel", headers=cabecera_cliente
    )

    assert primera.status_code == 200
    assert segunda.status_code == 409
    assert segunda.json().get("status") != ESTADO_CANCELADO


def test_un_horario_cancelado_queda_libre_para_agendar(
    cliente: TestClient,
    cabecera_cliente: dict[str, str],
    cuenta_veterinario: dict[str, Any],
) -> None:
    mascota = _registrar_mascota(cliente, cabecera_cliente)
    inicio = instante_futuro(LUNES, 10)
    turno = _agendar_turno(
        cliente,
        cabecera_cliente,
        pet_id=mascota["id"],
        vet_id=cuenta_veterinario["id"],
        inicio=inicio,
    )

    cancelacion = cliente.post(
        f"/appointments/{turno['id']}/cancel", headers=cabecera_cliente
    )
    nueva_reserva = _agendar_turno(
        cliente,
        cabecera_cliente,
        pet_id=mascota["id"],
        vet_id=cuenta_veterinario["id"],
        inicio=inicio,
    )

    assert cancelacion.status_code == 200
    assert nueva_reserva["start_at"] == _iso_utc(inicio)
    assert nueva_reserva["status"] == ESTADO_PROGRAMADO
