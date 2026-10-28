"""Servicio de mascotas de la clínica: alta y consulta por propietario.

El propietario de una mascota es siempre el cliente autenticado que la
registra: el servicio se encarga de comprobar el rol y de dejar la mascota
vinculada a su dueño, de modo que ninguna otra cuenta pueda consultarla.
"""

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import PermissionDeniedError
from app.models import Pet, User

# Únicos roles que pueden registrar mascotas en la clínica.
ROLES_QUE_REGISTRAN_MASCOTAS = ("client",)

# Especies que la clínica admite para una mascota.
ESPECIES_ADMITIDAS = ("dog", "cat", "other")


def crear_mascota(
    session: Session,
    *,
    propietario: User,
    nombre: str,
    especie: str,
    fecha_nacimiento: date,
) -> Pet:
    """Registra una mascota y la vincula con su propietario.

    Lanza ``PermissionDeniedError`` si quien llama no es un cliente: solo los
    clientes de la clínica pueden registrar mascotas.
    """
    if propietario.role not in ROLES_QUE_REGISTRAN_MASCOTAS:
        raise PermissionDeniedError("Solo los clientes pueden registrar mascotas.")
    if especie not in ESPECIES_ADMITIDAS:
        raise ValueError(f"Especie no admitida para una mascota: {especie!r}")

    mascota = Pet(
        name=nombre,
        species=especie,
        birth_date=fecha_nacimiento,
        owner_id=propietario.id,
    )
    session.add(mascota)
    session.commit()
    session.refresh(mascota)
    return mascota


def listar_mascotas_de(session: Session, propietario_id: int) -> list[Pet]:
    """Devuelve las mascotas del propietario indicado.

    El listado se ordena por identificador para que su respuesta sea estable
    entre llamadas.
    """
    consulta = select(Pet).where(Pet.owner_id == propietario_id).order_by(Pet.id)
    return list(session.execute(consulta).scalars())
