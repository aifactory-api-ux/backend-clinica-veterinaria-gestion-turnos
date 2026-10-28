"""Directorio de veterinarios de la clínica.

``GET /vets`` permite a cualquier cuenta autenticada consultar con qué
profesionales puede agendar un turno. El directorio solo expone el
identificador y el email de cada veterinario: ningún dato interno de la cuenta
sale por este endpoint.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas import VetResponse
from app.services import users

router = APIRouter(tags=["veterinarios"])


@router.get(
    "/vets",
    response_model=list[VetResponse],
    summary="Listado de los veterinarios de la clínica",
)
def listar_vets(
    session: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[User]:
    """Devuelve el directorio de veterinarios, con su ``id`` y su ``email``.

    Es un endpoint protegido: sin cabecera ``Authorization`` o con un token
    inválido la respuesta es ``401``.
    """
    return users.listar_veterinarios(session)
