"""Punto de entrada ASGI de la API de la clínica veterinaria."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.database import Base, engine
from app.errors import DomainError
from app.routers import appointments, auth, health, pets, vets


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Crea el esquema de la base de datos al arrancar la aplicación."""
    Base.metadata.create_all(bind=engine)
    yield


async def manejar_error_dominio(_: Request, error: DomainError) -> JSONResponse:
    """Traduce un error de dominio a la respuesta HTTP que le corresponde."""
    cabeceras = {"WWW-Authenticate": "Bearer"} if error.status_code == 401 else None
    return JSONResponse(
        status_code=error.status_code,
        content=error.to_body(),
        headers=cabeceras,
    )


def create_app() -> FastAPI:
    """Construye la instancia de la aplicación con sus rutas y manejadores."""
    application = FastAPI(
        title="API de la clínica veterinaria",
        description=(
            "Registro de usuarios y mascotas y gestión de turnos de la clínica."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )
    application.add_exception_handler(DomainError, manejar_error_dominio)
    application.include_router(health.router)
    application.include_router(auth.router)
    application.include_router(vets.router)
    application.include_router(pets.router)
    application.include_router(appointments.router)
    return application


app = create_app()
