"""Motor, sesión y base declarativa de la API."""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    """Base declarativa compartida por todos los modelos."""


engine = create_engine(settings.database_url, pool_pre_ping=True)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
    class_=Session,
)


def get_db() -> Iterator[Session]:
    """Entrega una sesión de base de datos por petición y la cierra al final."""
    with SessionLocal() as session:
        yield session


# La importación va al final del módulo a propósito: así los modelos quedan
# registrados en ``Base.metadata`` sin provocar un ciclo de importación.
from app import models  # noqa: E402,F401
