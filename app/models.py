"""Modelos de dominio de la clínica veterinaria."""

from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.engine import Dialect
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from app.database import Base


class UTCDateTime(TypeDecorator):
    """Instante temporal que se almacena y se recupera siempre en UTC.

    SQLite no guarda la zona horaria, por lo que al leer se reasocia ``UTC``;
    PostgreSQL devuelve el valor con zona y se convierte a UTC.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(
        self, value: datetime | None, dialect: Dialect
    ) -> datetime | None:
        """Normaliza a UTC el instante antes de escribirlo."""
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def process_result_value(
        self, value: datetime | None, dialect: Dialect
    ) -> datetime | None:
        """Devuelve el instante leído con la zona horaria UTC."""
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


def utc_now() -> datetime:
    """Instante actual en UTC."""
    return datetime.now(timezone.utc)


class User(Base):
    """Cuenta de la clínica: cliente o veterinario."""

    __tablename__ = "users"
    __table_args__ = (Index("uq_users_email", "email", unique=True),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime, nullable=False, default=utc_now
    )

    pets: Mapped[list["Pet"]] = relationship(back_populates="owner")
    vet_appointments: Mapped[list["Appointment"]] = relationship(
        back_populates="vet", foreign_keys="Appointment.vet_id"
    )


class Pet(Base):
    """Mascota registrada por un cliente de la clínica."""

    __tablename__ = "pets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    species: Mapped[str] = mapped_column(String(16), nullable=False)
    birth_date: Mapped[date] = mapped_column(Date, nullable=False)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime, nullable=False, default=utc_now
    )

    owner: Mapped["User"] = relationship(back_populates="pets")
    appointments: Mapped[list["Appointment"]] = relationship(back_populates="pet")


class Appointment(Base):
    """Turno agendado entre una mascota y un veterinario."""

    __tablename__ = "appointments"
    __table_args__ = (
        Index(
            "uq_appointments_vet_slot_scheduled",
            "vet_id",
            "start_at",
            unique=True,
            sqlite_where=text("status = 'scheduled'"),
            postgresql_where=text("status = 'scheduled'"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pet_id: Mapped[int] = mapped_column(ForeignKey("pets.id"), nullable=False)
    vet_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    start_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    end_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="scheduled"
    )
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime, nullable=False, default=utc_now
    )

    pet: Mapped["Pet"] = relationship(back_populates="appointments")
    vet: Mapped["User"] = relationship(
        back_populates="vet_appointments", foreign_keys=[vet_id]
    )
