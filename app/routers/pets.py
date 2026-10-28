"""Rutas de registro de mascotas de la clínica.

``POST /pets`` es exclusivo de los clientes: un veterinario que lo intenta
recibe ``403`` y no se registra ninguna mascota. ``GET /pets`` devuelve
únicamente las mascotas del usuario autenticado.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Pet, User
from app.schemas import PetCreateRequest, PetResponse
from app.services import pets

router = APIRouter(prefix="/pets", tags=["mascotas"])


@router.post(
    "",
    response_model=PetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Alta de una mascota del cliente autenticado",
)
def registrar_mascota(
    datos: PetCreateRequest,
    session: Session = Depends(get_db),
    propietario: User = Depends(get_current_user),
) -> Pet:
    """Registra una mascota a nombre del cliente autenticado.

    Responde ``403`` si quien llama no es un cliente y ``422`` si la especie o
    la fecha de nacimiento no cumplen las reglas de la clínica.
    """
    return pets.crear_mascota(
        session,
        propietario=propietario,
        nombre=datos.name,
        especie=datos.species,
        fecha_nacimiento=datos.birth_date,
    )


@router.get(
    "",
    response_model=list[PetResponse],
    summary="Listado de las mascotas del usuario autenticado",
)
def listar_mascotas(
    session: Session = Depends(get_db),
    propietario: User = Depends(get_current_user),
) -> list[Pet]:
    """Devuelve solo las mascotas propiedad del usuario autenticado.

    Es un endpoint protegido: sin cabecera ``Authorization`` o con un token
    inválido la respuesta es ``401``.
    """
    return pets.listar_mascotas_de(session, propietario.id)
