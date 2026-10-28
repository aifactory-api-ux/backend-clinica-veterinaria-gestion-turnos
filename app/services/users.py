"""Servicio de cuentas de la clínica: alta, autenticación y consulta.

La identidad de una cuenta es su email normalizado (``email.strip().lower()``):
las comparaciones se hacen siempre sobre esa forma, de modo que
``Ana@Example.com`` y ``ana@example.com`` son la misma cuenta.
"""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import DuplicateEmailError, InvalidCredentialsError
from app.models import User
from app.security import hash_password, verify_password

# Roles que la clínica admite. La capa de esquemas ya los restringe, pero el
# servicio mantiene el invariante para no persistir cuentas con otro rol.
ROLES_VALIDOS = ("client", "vet")


def normalizar_email(email: str) -> str:
    """Devuelve el email sin espacios y en minúsculas."""
    return email.strip().lower()


def buscar_usuario_por_email(session: Session, email: str) -> User | None:
    """Devuelve la cuenta con ese email normalizado, si existe."""
    consulta = select(User).where(User.email == normalizar_email(email))
    return session.execute(consulta).scalar_one_or_none()


def buscar_usuario_por_id(session: Session, user_id: int) -> User | None:
    """Devuelve la cuenta con ese identificador, si existe."""
    return session.get(User, user_id)


def crear_usuario(
    session: Session, *, email: str, password: str, role: str
) -> User:
    """Crea una cuenta con el email normalizado y la contraseña hasheada.

    Lanza ``DuplicateEmailError`` si el email ya está registrado: se comprueba
    antes de insertar y, además, se captura la violación de la restricción de
    unicidad por si dos altas simultáneas compiten por el mismo email.
    """
    if role not in ROLES_VALIDOS:
        raise ValueError(f"Rol no permitido para una cuenta de la clínica: {role!r}")

    correo = normalizar_email(email)
    if buscar_usuario_por_email(session, correo) is not None:
        raise DuplicateEmailError()

    usuario = User(email=correo, password_hash=hash_password(password), role=role)
    session.add(usuario)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise DuplicateEmailError() from exc
    session.refresh(usuario)
    return usuario


def listar_veterinarios(session: Session) -> list[User]:
    """Devuelve las cuentas de la clínica con rol ``vet``.

    El directorio se ordena por identificador para que su respuesta sea
    estable entre llamadas.
    """
    consulta = select(User).where(User.role == "vet").order_by(User.id)
    return list(session.execute(consulta).scalars())


def autenticar_usuario(session: Session, *, email: str, password: str) -> User:
    """Devuelve la cuenta cuyas credenciales coinciden.

    Lanza ``InvalidCredentialsError`` con el mismo detalle tanto si el email no
    está registrado como si la contraseña no coincide, para no revelar qué
    cuentas existen.
    """
    usuario = buscar_usuario_por_email(session, email)
    if usuario is None:
        raise InvalidCredentialsError()
    if not verify_password(password, usuario.password_hash):
        raise InvalidCredentialsError()
    return usuario
