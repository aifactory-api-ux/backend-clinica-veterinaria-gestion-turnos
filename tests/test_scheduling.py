"""Pruebas de las reglas de franja horaria de los turnos de la clínica.

Las reglas se verifican sobre instantes calculados, no sobre fechas fijas:
así la suite sigue siendo válida con el paso del tiempo y cada rechazo se
puede atribuir a una única regla.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.errors import InvalidSlotError
from app.services import scheduling
from tests.conftest import DOMINGO, LUNES, instante_futuro


def test_el_designador_z_se_interpreta_como_utc() -> None:
    inicio = scheduling.parse_start_at("2041-01-07T10:00:00Z")

    assert inicio == datetime(2041, 1, 7, 10, 0, tzinfo=timezone.utc)


def test_el_designador_de_desplazamiento_utc_se_interpreta_como_utc() -> None:
    inicio = scheduling.parse_start_at("2041-01-07T10:00:00+00:00")

    assert inicio == datetime(2041, 1, 7, 10, 0, tzinfo=timezone.utc)


def test_un_inicio_sin_zona_horaria_se_rechaza() -> None:
    with pytest.raises(InvalidSlotError):
        scheduling.parse_start_at("2041-01-07T10:00:00")


def test_un_inicio_que_no_es_iso_8601_se_rechaza() -> None:
    with pytest.raises(InvalidSlotError):
        scheduling.parse_start_at("07/01/2041 10:00")


def test_un_domingo_se_rechaza() -> None:
    inicio = instante_futuro(DOMINGO, 10)

    incumplidas = scheduling.validate_slot(inicio)

    assert scheduling.REGLA_DIA_SIN_CONSULTA in incumplidas


def test_una_hora_con_minutos_no_admitidos_se_rechaza() -> None:
    inicio = instante_futuro(LUNES, 10, 15)

    incumplidas = scheduling.validate_slot(inicio)

    assert scheduling.REGLA_MINUTOS in incumplidas


def test_una_hora_antes_de_la_apertura_se_rechaza() -> None:
    inicio = instante_futuro(LUNES, 8, 30)

    incumplidas = scheduling.validate_slot(inicio)

    assert scheduling.REGLA_FUERA_DE_FRANJA in incumplidas


def test_una_hora_despues_del_ultimo_inicio_se_rechaza() -> None:
    inicio = instante_futuro(LUNES, 18, 0)

    incumplidas = scheduling.validate_slot(inicio)

    assert scheduling.REGLA_FUERA_DE_FRANJA in incumplidas


def test_el_ultimo_inicio_del_dia_se_acepta() -> None:
    inicio = instante_futuro(LUNES, 17, 30)

    assert scheduling.validate_slot(inicio) == []
    fin = scheduling.slot_end(inicio)
    assert (fin.hour, fin.minute) == (18, 0)


def test_un_instante_pasado_se_rechaza() -> None:
    inicio = datetime.now(timezone.utc) - timedelta(days=1)

    incumplidas = scheduling.validate_slot(inicio)

    assert scheduling.REGLA_INICIO_PASADO in incumplidas


def test_un_horario_valido_no_incumple_ninguna_regla() -> None:
    inicio = instante_futuro(LUNES, 10, 30)

    assert scheduling.validate_slot(inicio) == []


def test_las_reglas_se_evaluan_en_orden() -> None:
    domingo_pasado = instante_futuro(DOMINGO, 10) - timedelta(days=7)

    incumplidas = scheduling.validate_slot(domingo_pasado)

    assert incumplidas == [
        scheduling.REGLA_INICIO_PASADO,
        scheduling.REGLA_DIA_SIN_CONSULTA,
    ]


def test_el_final_del_turno_es_treinta_minutos_despues() -> None:
    inicio = instante_futuro(LUNES, 10)

    assert scheduling.slot_end(inicio) - inicio == timedelta(minutes=30)


def test_exigir_un_slot_valido_no_falla_con_un_horario_admitido() -> None:
    scheduling.exigir_slot_valido(instante_futuro(LUNES, 9))


def test_exigir_un_slot_valido_falla_con_un_horario_rechazado() -> None:
    with pytest.raises(InvalidSlotError):
        scheduling.exigir_slot_valido(instante_futuro(LUNES, 18, 0))
