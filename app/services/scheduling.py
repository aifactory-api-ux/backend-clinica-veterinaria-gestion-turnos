"""Reglas de franja horaria de los turnos de la clínica.

Son funciones puras sobre instantes UTC: no consultan la base de datos ni
dependen de la petición HTTP, de modo que se pueden verificar de forma
aislada. El día de la semana y la hora se evalúan siempre sobre el reloj
UTC, que es la zona horaria en la que se define ``start_at``.
"""

from datetime import datetime, time, timedelta, timezone

from app.errors import InvalidSlotError

# Duración de cada turno de la clínica.
DURACION_TURNO = timedelta(minutes=30)

# Franja de inicio admitida, en hora UTC.
HORA_APERTURA = time(9, 0)
HORA_ULTIMO_INICIO = time(17, 30)

# Minutos admitidos para el inicio de un turno.
MINUTOS_ADMITIDOS = (0, 30)

# Días con consulta: de lunes (0) a sábado (5); el domingo (6) no se atiende.
DIAS_CON_CONSULTA = (0, 1, 2, 3, 4, 5)

# Identificadores de las reglas, evaluadas siempre en este orden.
REGLA_INICIO_PASADO = "inicio_en_pasado"
REGLA_DIA_SIN_CONSULTA = "dia_sin_consulta"
REGLA_MINUTOS = "minutos_no_admitidos"
REGLA_FUERA_DE_FRANJA = "fuera_de_franja_horaria"

# Descripción de cada regla, para el detalle del error de validación.
DESCRIPCIONES_REGLAS = {
    REGLA_INICIO_PASADO: "el inicio del turno no puede estar en el pasado",
    REGLA_DIA_SIN_CONSULTA: "el inicio del turno debe caer de lunes a sábado",
    REGLA_MINUTOS: "el inicio del turno debe ser en punto o en media hora",
    REGLA_FUERA_DE_FRANJA: (
        "el inicio del turno debe estar entre las 09:00 y las 17:30 (UTC)"
    ),
}


def parse_start_at(valor: str | datetime) -> datetime:
    """Convierte el inicio recibido en un instante con zona horaria UTC.

    Admite un texto ISO 8601 con designador de zona (``Z`` u offset) o un
    ``datetime`` ya construido. Lanza ``InvalidSlotError`` (422) si el valor
    no es ISO 8601 o si no identifica un instante con zona horaria, porque en
    ese caso no se sabe a qué momento de la agenda corresponde.
    """
    if isinstance(valor, datetime):
        instante = valor
    else:
        try:
            instante = datetime.fromisoformat(str(valor).strip())
        except (TypeError, ValueError) as exc:
            raise InvalidSlotError(
                "El inicio del turno debe ser un instante ISO 8601 en UTC."
            ) from exc

    if instante.tzinfo is None:
        raise InvalidSlotError(
            "El inicio del turno debe indicar la zona horaria UTC."
        )
    return instante.astimezone(timezone.utc)


def validate_slot(inicio: datetime, ahora: datetime | None = None) -> list[str]:
    """Devuelve las reglas incumplidas por el inicio indicado.

    La lista va vacía cuando el inicio cumple todas las reglas de la
    clínica. Las reglas se evalúan en el orden en que las fija el diseño:
    inicio en el pasado, día de la semana, minutos y franja horaria.
    """
    momento = datetime.now(timezone.utc) if ahora is None else ahora
    inicio_utc = inicio.astimezone(timezone.utc)

    incumplidas: list[str] = []
    if inicio_utc <= momento:
        incumplidas.append(REGLA_INICIO_PASADO)
    if inicio_utc.weekday() not in DIAS_CON_CONSULTA:
        incumplidas.append(REGLA_DIA_SIN_CONSULTA)
    if inicio_utc.minute not in MINUTOS_ADMITIDOS or inicio_utc.second != 0:
        incumplidas.append(REGLA_MINUTOS)
    if not HORA_APERTURA <= inicio_utc.time() <= HORA_ULTIMO_INICIO:
        incumplidas.append(REGLA_FUERA_DE_FRANJA)
    return incumplidas


def slot_end(inicio: datetime) -> datetime:
    """Devuelve el final del turno: 30 minutos después de su inicio."""
    return inicio + DURACION_TURNO


def exigir_slot_valido(inicio: datetime, ahora: datetime | None = None) -> None:
    """Comprueba el inicio del turno y lanza ``InvalidSlotError`` si falla.

    El detalle del error enumera las reglas incumplidas, de modo que el
    equipo de la clínica sepa qué debe corregir.
    """
    incumplidas = validate_slot(inicio, ahora)
    if incumplidas:
        motivos = "; ".join(DESCRIPCIONES_REGLAS[regla] for regla in incumplidas)
        raise InvalidSlotError(f"El horario solicitado no es válido: {motivos}.")
