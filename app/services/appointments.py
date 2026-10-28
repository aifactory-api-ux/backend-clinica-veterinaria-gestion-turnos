"""Servicio de turnos de la clínica: disponibilidad, creación, consulta y cancelación.

El servicio aplica las reglas de la clínica en el orden en que las fija el
diseño, para que el código de respuesta no dependa de cuántos problemas
haya a la vez: rol del solicitante, existencia de la mascota, propiedad de la
mascota, existencia del veterinario, reglas de franja horaria y, por
último, disponibilidad de la agenda del veterinario.
"""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import (
    AppointmentAlreadyCancelledError,
    AppointmentConflictError,
    PermissionDeniedError,
    ResourceNotFoundError,
)
from app.models import Appointment, Pet, User
from app.services import scheduling

# Únicos roles que pueden agendar turnos en la clínica.
ROLES_QUE_AGENDAN = ("client",)

# Rol que ve los turnos en los que atiende.
ROL_VETERINARIO = "vet"

# Rol que ve los turnos de sus propias mascotas.
ROL_CLIENTE = "client"

# Estados posibles de un turno.
ESTADO_PROGRAMADO = "scheduled"
ESTADO_CANCELADO = "cancelled"


def buscar_turno_solapado(
    session: Session, *, vet_id: int, inicio: datetime, fin: datetime
) -> bool:
    """Indica si el veterinario tiene un turno activo que solapa el intervalo.

    Solo se consideran los turnos programados: un turno cancelado deja el
    horario libre y no bloquea una nueva reserva. La comparación se hace por
    solapamiento de intervalos, de modo que la regla siga siendo correcta
    si la duración de los turnos cambia.
    """
    consulta = (
        select(Appointment.id)
        .where(
            Appointment.vet_id == vet_id,
            Appointment.status == ESTADO_PROGRAMADO,
            Appointment.start_at < fin,
            Appointment.end_at > inicio,
        )
        .limit(1)
    )
    return session.execute(consulta).first() is not None


def crear_turno(
    session: Session,
    *,
    cliente: User,
    pet_id: int,
    vet_id: int,
    inicio: datetime | str,
) -> Appointment:
    """Agenda un turno de 30 minutos para una mascota del cliente indicado.

    Lanza ``PermissionDeniedError`` (403) si quien llama no es un cliente o
    si la mascota no es suya, ``ResourceNotFoundError`` (404) si la mascota o
    el veterinario no existen, ``InvalidSlotError`` (422) si el inicio no
    cumple las reglas de franja horaria y ``AppointmentConflictError`` (409)
    si el veterinario ya tiene un turno activo en ese horario.
    """
    if cliente.role not in ROLES_QUE_AGENDAN:
        raise PermissionDeniedError("Solo los clientes pueden agendar turnos.")

    mascota = session.get(Pet, pet_id)
    if mascota is None:
        raise ResourceNotFoundError("La mascota no existe.")
    if mascota.owner_id != cliente.id:
        raise PermissionDeniedError(
            "Solo se pueden agendar turnos para las mascotas propias."
        )

    veterinario = session.get(User, vet_id)
    if veterinario is None or veterinario.role != "vet":
        raise ResourceNotFoundError("El veterinario no existe.")

    inicio_utc = scheduling.parse_start_at(inicio)
    scheduling.exigir_slot_valido(inicio_utc)
    fin = scheduling.slot_end(inicio_utc)

    if buscar_turno_solapado(
        session, vet_id=veterinario.id, inicio=inicio_utc, fin=fin
    ):
        raise AppointmentConflictError()

    turno = Appointment(
        pet_id=mascota.id,
        vet_id=veterinario.id,
        start_at=inicio_utc,
        end_at=fin,
        status=ESTADO_PROGRAMADO,
    )
    session.add(turno)
    try:
        session.commit()
    except IntegrityError as exc:
        # El índice único parcial del modelo impide la doble reserva aunque
        # dos peticiones compitan por el mismo horario.
        session.rollback()
        raise AppointmentConflictError() from exc
    session.refresh(turno)
    return turno


def listar_turnos(session: Session, usuario: User) -> list[Appointment]:
    """Devuelve los turnos que le corresponden al usuario indicado.

    Un cliente ve los turnos de sus propias mascotas y un veterinario los
    turnos en los que atiende: cada rol consulta únicamente su parte de la
    agenda. El listado se ordena por hora de inicio, de modo que la agenda
    salga en orden cronológico y la respuesta sea estable entre llamadas.
    """
    if usuario.role == ROL_VETERINARIO:
        consulta = select(Appointment).where(Appointment.vet_id == usuario.id)
    elif usuario.role == ROL_CLIENTE:
        consulta = (
            select(Appointment)
            .join(Pet, Appointment.pet_id == Pet.id)
            .where(Pet.owner_id == usuario.id)
        )
    else:
        return []

    consulta = consulta.order_by(Appointment.start_at, Appointment.id)
    return list(session.execute(consulta).scalars())


def cancelar_turno(session: Session, *, turno_id: int, usuario: User) -> Appointment:
    """Cancela un turno y lo devuelve con su estado ya actualizado.

    Solo el cliente dueño de la mascota o el veterinario que atiende el turno
    pueden cancelarlo. Lanza ``ResourceNotFoundError`` (404) si el turno no
    existe, ``PermissionDeniedError`` (403) si quien llama no está relacionado
    con el turno y ``AppointmentAlreadyCancelledError`` (409) si el turno ya
    estaba cancelado.
    """
    turno = session.get(Appointment, turno_id)
    if turno is None:
        raise ResourceNotFoundError("El turno no existe.")

    mascota = session.get(Pet, turno.pet_id)
    es_dueno = mascota is not None and mascota.owner_id == usuario.id
    es_veterinario = turno.vet_id == usuario.id
    if not es_dueno and not es_veterinario:
        raise PermissionDeniedError(
            "Solo el dueño de la mascota o el veterinario del turno pueden cancelarlo."
        )

    if turno.status == ESTADO_CANCELADO:
        raise AppointmentAlreadyCancelledError()

    turno.status = ESTADO_CANCELADO
    session.commit()
    session.refresh(turno)
    return turno
