"""Errores de dominio de la clínica y su equivalencia en códigos HTTP."""

from typing import Any


class DomainError(Exception):
    """Error de dominio: se traduce a una respuesta HTTP con ``detail``."""

    status_code: int = 500
    default_detail: str = "Error interno del servicio."

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail or self.default_detail
        super().__init__(self.detail)

    def to_body(self) -> dict[str, Any]:
        """Cuerpo JSON con el que se responde al cliente."""
        return {"detail": self.detail}


class AuthenticationError(DomainError):
    """Falta autenticación o el token presentado no es válido."""

    status_code = 401
    default_detail = "Credenciales o token de acceso inválidos."


class InvalidCredentialsError(AuthenticationError):
    """El email o la contraseña no corresponden a una cuenta registrada."""

    default_detail = "Credenciales inválidas."


class PermissionDeniedError(DomainError):
    """El usuario autenticado no tiene permiso para la operación solicitada."""

    status_code = 403
    default_detail = "No tiene permisos para realizar esta operación."


class ResourceNotFoundError(DomainError):
    """El recurso solicitado no existe."""

    status_code = 404
    default_detail = "Recurso no encontrado."


class ConflictError(DomainError):
    """La operación entra en conflicto con el estado actual del recurso."""

    status_code = 409
    default_detail = "La operación entra en conflicto con el estado actual."


class DuplicateEmailError(ConflictError):
    """Ya existe una cuenta registrada con el mismo email."""

    default_detail = "El email ya está registrado."


class AppointmentConflictError(ConflictError):
    """El veterinario ya tiene un turno activo en ese horario."""

    default_detail = "El veterinario ya tiene un turno en ese horario."


class AppointmentAlreadyCancelledError(ConflictError):
    """El turno ya estaba cancelado y no se puede cancelar de nuevo."""

    default_detail = "El turno ya está cancelado."


class InvalidSlotError(DomainError):
    """El inicio del turno no cumple las reglas de franja horaria."""

    status_code = 422
    default_detail = "El horario solicitado no cumple las reglas de la clínica."
