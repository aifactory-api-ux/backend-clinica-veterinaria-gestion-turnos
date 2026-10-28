"""Rutas de autenticación: alta de cuentas e inicio de sesión.

Ambos endpoints son públicos: no declaran la dependencia ``get_current_user``,
de modo que un cliente puede registrarse y obtener su token sin estar
autenticado.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import (
    LoginRequest,
    TokenResponse,
    UserRegisterRequest,
    UserResponse,
)
from app.security import create_access_token
from app.services import users

router = APIRouter(prefix="/auth", tags=["autenticación"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Alta de una cuenta de cliente o veterinario",
)
def registrar(
    datos: UserRegisterRequest, session: Session = Depends(get_db)
) -> User:
    """Crea una cuenta nueva y devuelve sus datos públicos.

    Responde ``409`` si el email ya está registrado y ``422`` si la contraseña
    tiene menos de 8 caracteres o el rol no es ``client`` ni ``vet``.
    """
    return users.crear_usuario(
        session, email=datos.email, password=datos.password, role=datos.role
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Inicio de sesión con emisión de token Bearer",
)
def iniciar_sesion(
    datos: LoginRequest, session: Session = Depends(get_db)
) -> TokenResponse:
    """Valida las credenciales y emite un token JWT de acceso.

    Responde ``401`` si el email no está registrado o la contraseña no
    coincide, sin distinguir entre ambos casos.
    """
    usuario = users.autenticar_usuario(
        session, email=datos.email, password=datos.password
    )
    return TokenResponse(access_token=create_access_token(usuario.id, usuario.role))
