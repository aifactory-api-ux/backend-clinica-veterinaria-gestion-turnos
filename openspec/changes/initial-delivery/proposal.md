# Proposal

## Why

La clínica veterinaria no tiene ningún backend: no hay forma de registrar clientes ni veterinarios, de gestionar las mascotas de cada cliente ni de agendar y cancelar turnos con control de horarios y de solapamientos. Se necesita una API REST con FastAPI y PostgreSQL que exponga ese flujo completo, lista para que el equipo interno de la clínica pueda empezar a usarla desde el primer día.

## What Changes

- Se introduce una API REST con FastAPI respaldada por PostgreSQL que expone el flujo completo de una clínica veterinaria: alta de usuarios, registro de mascotas y gestión de turnos.
- Se añade `GET /health` como endpoint público de comprobación de estado.
- Se añade registro de usuarios con `POST /auth/register` (`role` `client` o `vet`), con control de email duplicado, longitud mínima de contraseña y validez del rol.
- Se añade autenticación con `POST /auth/login`, que emite un JWT (`access_token`, `token_type: "bearer"`) y protege con `Authorization: Bearer` todos los endpoints salvo health, register y login.
- Se añade `GET /vets` para consultar el directorio de veterinarios disponibles.
- Se añade el registro de mascotas con `POST /pets` (exclusivo de clientes) y la consulta `GET /pets` limitada a las mascotas del cliente autenticado.
- Se añade la gestión de turnos con `POST /appointments`, `GET /appointments` y `POST /appointments/{id}/cancel`, aplicando las reglas de franja horaria, duración de 30 minutos, propiedad de la mascota y no solapamiento por veterinario.
- Se añade la contenerización del proyecto: un `Dockerfile` y un `docker-compose.yml` en la raíz que construyen y ejecutan la API con PostgreSQL.

## Capabilities

### New Capabilities

- `service-health`: endpoint público de comprobación de estado del servicio.
- `user-auth`: registro, autenticación por JWT y aplicación de la autorización `Authorization: Bearer` en los endpoints protegidos.
- `vet-directory`: consulta del directorio de veterinarios disponibles para agendar turnos.
- `pets`: alta de mascotas por parte de clientes y consulta de las mascotas propias del cliente autenticado.
- `appointments`: creación, consulta y cancelación de turnos con reglas de franja horaria, duración, propiedad de la mascota y conflicto de agenda del veterinario.
- `container-runtime`: construcción y ejecución del proyecto mediante `Dockerfile` y `docker-compose.yml` en la raíz del repositorio.

### Modified Capabilities

Ninguna. El repositorio parte sin especificaciones publicadas, por lo que todas las capacidades de este cambio son nuevas.

## Impact

- Código nuevo de la API (FastAPI), capa de persistencia (PostgreSQL) y esquema de datos para usuarios, mascotas y turnos.
- Dependencias de runtime: FastAPI, servidor ASGI, ORM/migraciones de PostgreSQL, librería de JWT y hashing de contraseñas.
- Contrato HTTP nuevo y completo: `/health`, `/auth/register`, `/auth/login`, `/vets`, `/pets`, `/appointments`, `/appointments/{id}/cancel`.
- Archivos de operación nuevos en la raíz: `Dockerfile` y `docker-compose.yml`, con PostgreSQL como servicio de base de datos.
- Sin impacto sobre sistemas existentes: es la primera entrega del repositorio.
