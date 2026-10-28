"""Pruebas de persistencia: creación del esquema, instantes UTC y unicidad."""

from collections.abc import Iterator
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import Appointment, Pet, User

INICIO = datetime(2041, 1, 7, 10, 0, tzinfo=timezone.utc)
FIN = INICIO + timedelta(minutes=30)


@pytest.fixture
def engine_de_pruebas() -> Iterator[Engine]:
    """Motor SQLite en memoria, aislado por test, con el esquema ya creado."""
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


def _crear_cuentas(session: Session) -> tuple[int, int, int]:
    """Crea un cliente, su mascota y un veterinario; devuelve sus identificadores."""
    cliente = User(email="ana@example.com", password_hash="hash", role="client")
    session.add(cliente)
    session.flush()

    mascota = Pet(
        name="Firulais",
        species="dog",
        birth_date=date(2020, 5, 10),
        owner_id=cliente.id,
    )
    session.add(mascota)
    session.flush()

    veterinario = User(email="dr.vega@example.com", password_hash="hash", role="vet")
    session.add(veterinario)
    session.flush()

    return cliente.id, mascota.id, veterinario.id


def test_el_esquema_se_crea_en_el_motor_de_pruebas(engine_de_pruebas: Engine) -> None:
    tablas = set(inspect(engine_de_pruebas).get_table_names())

    assert tablas == {"users", "pets", "appointments"}


def test_los_instantes_utc_se_conservan_al_crear_y_al_leer(
    engine_de_pruebas: Engine,
) -> None:
    with Session(engine_de_pruebas) as session:
        cliente_id, mascota_id, veterinario_id = _crear_cuentas(session)
        turno = Appointment(
            pet_id=mascota_id,
            vet_id=veterinario_id,
            start_at=INICIO,
            end_at=FIN,
            status="scheduled",
        )
        session.add(turno)
        session.commit()
        turno_id = turno.id

    with Session(engine_de_pruebas) as session:
        usuario = session.get(User, cliente_id)
        mascota = session.get(Pet, mascota_id)
        turno = session.get(Appointment, turno_id)

        assert usuario is not None
        assert usuario.email == "ana@example.com"
        assert usuario.role == "client"
        assert usuario.created_at.tzinfo is timezone.utc

        assert mascota is not None
        assert mascota.name == "Firulais"
        assert mascota.species == "dog"
        assert mascota.birth_date == date(2020, 5, 10)
        assert mascota.owner_id == cliente_id

        assert turno is not None
        assert turno.start_at == INICIO
        assert turno.start_at.tzinfo is timezone.utc
        assert turno.end_at == FIN
        assert turno.end_at.tzinfo is timezone.utc
        assert turno.status == "scheduled"


def test_un_instante_con_desplazamiento_se_normaliza_a_utc(
    engine_de_pruebas: Engine,
) -> None:
    instante_local = datetime(2041, 1, 7, 12, 0, tzinfo=timezone(timedelta(hours=2)))

    with Session(engine_de_pruebas) as session:
        cliente_id, mascota_id, veterinario_id = _crear_cuentas(session)
        turno = Appointment(
            pet_id=mascota_id,
            vet_id=veterinario_id,
            start_at=instante_local,
            end_at=instante_local + timedelta(minutes=30),
            status="scheduled",
        )
        session.add(turno)
        session.commit()
        turno_id = turno.id

    with Session(engine_de_pruebas) as session:
        turno = session.get(Appointment, turno_id)

        assert turno is not None
        assert turno.start_at == INICIO
        assert turno.start_at == datetime(2041, 1, 7, 10, 0, tzinfo=timezone.utc)


def test_la_base_de_datos_rechaza_un_segundo_turno_programado_del_mismo_veterinario(
    engine_de_pruebas: Engine,
) -> None:
    with Session(engine_de_pruebas) as session:
        _, mascota_id, veterinario_id = _crear_cuentas(session)
        for _ in range(2):
            session.add(
                Appointment(
                    pet_id=mascota_id,
                    vet_id=veterinario_id,
                    start_at=INICIO,
                    end_at=FIN,
                    status="scheduled",
                )
            )

        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


def test_un_turno_cancelado_no_ocupa_el_hueco_del_veterinario(
    engine_de_pruebas: Engine,
) -> None:
    with Session(engine_de_pruebas) as session:
        _, mascota_id, veterinario_id = _crear_cuentas(session)
        session.add(
            Appointment(
                pet_id=mascota_id,
                vet_id=veterinario_id,
                start_at=INICIO,
                end_at=FIN,
                status="cancelled",
            )
        )
        session.add(
            Appointment(
                pet_id=mascota_id,
                vet_id=veterinario_id,
                start_at=INICIO,
                end_at=FIN,
                status="scheduled",
            )
        )
        session.commit()

        programados = (
            session.query(Appointment)
            .filter(Appointment.status == "scheduled")
            .count()
        )

        assert programados == 1


def test_la_base_de_datos_rechaza_dos_cuentas_con_el_mismo_email(
    engine_de_pruebas: Engine,
) -> None:
    with Session(engine_de_pruebas) as session:
        session.add(User(email="ana@example.com", password_hash="hash", role="client"))
        session.add(
            User(email="ana@example.com", password_hash="otro-hash", role="client")
        )

        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


def test_el_indice_parcial_esta_declarado_para_sqlite_y_postgresql() -> None:
    indice = next(
        indice
        for indice in Appointment.__table__.indexes
        if indice.name == "uq_appointments_vet_slot_scheduled"
    )

    assert indice.unique is True
    assert [columna.name for columna in indice.columns] == ["vet_id", "start_at"]
    assert indice.dialect_options["sqlite"]["where"] is not None
    assert indice.dialect_options["postgresql"]["where"] is not None


def test_el_indice_de_email_es_unico_en_la_base_de_datos(
    engine_de_pruebas: Engine,
) -> None:
    indices = inspect(engine_de_pruebas).get_indexes("users")

    indice_email = next(
        indice for indice in indices if indice["name"] == "uq_users_email"
    )

    assert indice_email["unique"] == 1
    assert indice_email["column_names"] == ["email"]
