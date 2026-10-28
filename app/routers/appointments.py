"""Rutas de gestión de turnos de la clínica.

``POST /appointments`` agenda un turno de 30 minutos para una mascota del
cliente autenticado. El servicio comprueba, en este orden, el rol del
solicitante, la existencia y la propiedad de la mascota, la existencia del
veterinario, las reglas de franja horaria y la disponibilidad de la agenda.

``GET /appointments`` devuelve los turnos que le corresponden al usuario
autenticado: los de sus mascotas si es cliente y los que atiende si es
veterinario. ``POST /appointments/{id}/cancel`` cancela un turno y solo
acepta al dueño de la mascota o al veterinario del turno.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Appointment, User
from app.schemas import AppointmentCreateRequest, AppointmentResponse
from app.services import appointments

router = APIRouter(prefix="/appointments", tags=["turnos"])


@router.post(
    "",
    response_model=AppointmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Agendar de un turno para una mascota del cliente autenticado",
)
def agendar_turno(
    datos: AppointmentCreateRequest,
    session: Session = Depends(get_db),
    cliente: User = Depends(get_current_user),
) -> Appointment:
    """Agenda un turno para una mascota del cliente autenticado.

    Responde ``403`` si quien llama no es un cliente o si la mascota es de
    otro cliente, ``404`` si la mascota o el veterinario no existen, ``422``
    si el inicio no cumple las reglas de franja horaria y ``409`` si el
    veterinario ya tiene un turno activo en ese horario.
    """
    return appointments.crear_turno(
        session,
        cliente=cliente,
        pet_id=datos.pet_id,
        vet_id=datos.vet_id,
        inicio=datos.start_at,
    )


@router.get(
    "",
    response_model=list[AppointmentResponse],
    summary="Listado de los turnos del usuario autenticado",
)
def listar_turnos(
    session: Session = Depends(get_db),
    usuario: User = Depends(get_current_user),
) -> list[Appointment]:
    """Devuelve los turnos del cliente o del veterinario autenticado.

    Un cliente recibe los turnos de sus propias mascotas y un veterinario los
    turnos en los que atiende. Es un endpoint protegido: sin cabecera
    ``Authorization`` o con un token inválido la respuesta es ``401``.
    """
    return appointments.listar_turnos(session, usuario=usuario)


@router.post(
    "/{id}/cancel",
    response_model=AppointmentResponse,
    summary="Cancelación de un turno por su dueño o por su veterinario",
)
def cancelar_turno(
    id: int,
    session: Session = Depends(get_db),
    usuario: User = Depends(get_current_user),
) -> Appointment:
    """Cancela un turno y lo devuelve con su estado ya actualizado.

    Responde ``404`` si el turno no existe, ``403`` si quien llama no es el
    dueño de la mascota ni el veterinario del turno y ``409`` si el turno ya
    estaba cancelado.
    """
    return appointments.cancelar_turno(session, turno_id=id, usuario=usuario)
