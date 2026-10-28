"""Esquemas de entrada y salida de la API de la clínica veterinaria.

Los esquemas fijan la forma del contrato HTTP: las reglas de forma (longitud
mínima de la contraseña, conjunto de roles admitidos) viven aquí y se traducen
en respuestas ``422`` de FastAPI; las reglas de negocio (email duplicado,
credenciales incorrectas) viven en ``app/services`` y se traducen en ``409`` y
``401``.
"""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Único conjunto de roles que admite la clínica: cliente y veterinario.
Role = Literal["client", "vet"]

# Únicas especies que admite la clínica para una mascota.
Especie = Literal["dog", "cat", "other"]

# Longitud mínima exigida a las contraseñas de la clínica.
LONGITUD_MINIMA_CONTRASENA = 8

# Longitud máxima del nombre de una mascota, igual que la de la columna.
LONGITUD_MAXIMA_NOMBRE_MASCOTA = 120


class UserRegisterRequest(BaseModel):
    """Datos de alta de una cuenta de cliente o veterinario."""

    email: str = Field(description="Correo electrónico de la cuenta.")
    password: str = Field(
        min_length=LONGITUD_MINIMA_CONTRASENA,
        description="Contraseña de la cuenta, de al menos 8 caracteres.",
    )
    role: Role = Field(description="Rol de la cuenta: `client` o `vet`.")


class UserResponse(BaseModel):
    """Datos públicos de una cuenta de la clínica."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    role: str


class VetResponse(BaseModel):
    """Datos públicos de un veterinario del directorio de la clínica."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str


class LoginRequest(BaseModel):
    """Credenciales de acceso a la API."""

    email: str = Field(description="Correo electrónico de la cuenta.")
    password: str = Field(description="Contraseña de la cuenta.")


class TokenResponse(BaseModel):
    """Token de acceso emitido tras un inicio de sesión correcto."""

    access_token: str = Field(
        description="Token JWT que se envía en la cabecera `Authorization`."
    )
    token_type: Literal["bearer"] = "bearer"


class PetCreateRequest(BaseModel):
    """Datos de alta de una mascota."""

    name: str = Field(
        max_length=LONGITUD_MAXIMA_NOMBRE_MASCOTA,
        description="Nombre de la mascota.",
    )
    species: Especie = Field(
        description="Especie de la mascota: `dog`, `cat` u `other`."
    )
    birth_date: date = Field(
        description="Fecha de nacimiento de la mascota, en formato `AAAA-MM-DD`."
    )

    @field_validator("birth_date")
    @classmethod
    def _rechazar_fecha_de_nacimiento_futura(cls, value: date) -> date:
        """Impide que la fecha de nacimiento sea posterior al día de hoy."""
        if value > date.today():
            raise ValueError("La fecha de nacimiento no puede ser futura.")
        return value


class PetResponse(BaseModel):
    """Datos públicos de una mascota registrada en la clínica."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    species: str
    birth_date: date
    owner_id: int


class AppointmentCreateRequest(BaseModel):
    """Datos de alta de un turno."""

    pet_id: int = Field(
        description="Identificador de la mascota que atiende el turno."
    )
    vet_id: int = Field(
        description="Identificador del veterinario que atiende el turno."
    )
    start_at: datetime = Field(
        description="Inicio del turno, en instante UTC ISO 8601."
    )


class AppointmentResponse(BaseModel):
    """Datos públicos de un turno de la clínica."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    pet_id: int
    vet_id: int
    start_at: datetime
    end_at: datetime
    status: str
