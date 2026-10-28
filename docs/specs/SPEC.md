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


<!-- specs/appointments/spec.md -->
# Spec Delta

## Purpose

Cubre la gestión de turnos de la clínica veterinaria: creación con validación de franja horaria y ausencia de solapamientos por veterinario, consulta según el rol del usuario autenticado y cancelación por el dueño de la mascota o por el veterinario del turno.

## ADDED Requirements

### Requirement: Client schedules an appointment

The service SHALL expose `POST /appointments` accepting `pet_id`, `vet_id` and `start_at` in UTC ISO 8601, and SHALL answer HTTP 201 with the JSON body `{"id": ..., "pet_id": ..., "vet_id": ..., "start_at": ..., "end_at": ..., "status": "scheduled"}`.

#### Scenario: Scheduling an appointment for an owned pet

- **WHEN** an authenticated client posts `{"pet_id": 12, "vet_id": 3, "start_at": "2041-01-07T10:00:00Z"}` to `/appointments` and pet `12` belongs to that client
- **THEN** the response status is 201 and the body contains a non-empty `id`, `pet_id` equal to `12`, `vet_id` equal to `3`, `start_at` equal to `2041-01-07T10:00:00Z` and `status` equal to `scheduled`

### Requirement: Appointments last 30 minutes

The service SHALL set the `end_at` of a scheduled appointment to exactly 30 minutes after its `start_at`.

#### Scenario: End time is derived from the start time

- **WHEN** an authenticated client schedules an appointment with `start_at` equal to `2041-01-07T10:00:00Z`
- **THEN** the response body contains `end_at` equal to `2041-01-07T10:30:00Z`

### Requirement: Only clients may schedule appointments

The service SHALL answer HTTP 403 when `POST /appointments` is called by an authenticated user whose role is `vet`, and SHALL NOT create the appointment.

#### Scenario: A veterinarian tries to schedule an appointment

- **WHEN** an authenticated user with role `vet` posts `{"pet_id": 12, "vet_id": 3, "start_at": "2041-01-07T10:00:00Z"}` to `/appointments`
- **THEN** the response status is 403 and the response body contains no `id` of a created appointment

### Requirement: Appointments require an owned pet

The service SHALL answer HTTP 403 when `POST /appointments` refers to a pet that exists but is not owned by the authenticated client, and SHALL NOT create the appointment.

#### Scenario: Scheduling with a pet of another client

- **WHEN** an authenticated client posts `{"pet_id": 12, "vet_id": 3, "start_at": "2041-01-07T10:00:00Z"}` to `/appointments` and pet `12` belongs to another client
- **THEN** the response status is 403 and the response body contains no `id` of a created appointment

### Requirement: Unknown pets and veterinarians are reported as not found

The service SHALL answer HTTP 404 when `POST /appointments` refers to a `pet_id` that does not exist or to a `vet_id` that does not exist, and SHALL NOT create the appointment.

#### Scenario: Scheduling with a pet that does not exist

- **WHEN** an authenticated client posts `{"pet_id": 999999, "vet_id": 3, "start_at": "2041-01-07T10:00:00Z"}` to `/appointments`
- **THEN** the response status is 404 and the response body contains no `id` of a created appointment

#### Scenario: Scheduling with a veterinarian that does not exist

- **WHEN** an authenticated client posts `{"pet_id": 12, "vet_id": 999999, "start_at": "2041-01-07T10:00:00Z"}` to `/appointments`
- **THEN** the response status is 404 and the response body contains no `id` of a created appointment

### Requirement: Appointment start is a UTC ISO 8601 instant

The service SHALL accept a `start_at` that carries an explicit UTC designator (`Z` or `+00:00`), and SHALL answer HTTP 422 when the submitted value does not identify a UTC instant.

#### Scenario: Scheduling without a UTC designator

- **WHEN** an authenticated client posts `{"pet_id": 12, "vet_id": 3, "start_at": "2041-01-07T10:00:00"}` to `/appointments`
- **THEN** the response status is 422 and the response body contains no `id` of a created appointment

### Requirement: Appointments start on a working day

The service SHALL accept appointment start dates only from Monday to Saturday, and SHALL answer HTTP 422 for a start date falling on a Sunday.

#### Scenario: Scheduling on a Sunday

- **WHEN** an authenticated client posts `{"pet_id": 12, "vet_id": 3, "start_at": "2041-01-13T10:00:00Z"}` to `/appointments`
- **THEN** the response status is 422 and the response body contains no `id` of a created appointment

### Requirement: Appointments start on a half-hour boundary inside the opening hours

The service SHALL accept appointment start times only when the UTC minutes are `00` or `30` and the UTC time is between `09:00` and `17:30` inclusive, so that the last start of the day is `17:30`, and SHALL answer HTTP 422 otherwise.

#### Scenario: Scheduling with minutes that are not 00 or 30

- **WHEN** an authenticated client posts `{"pet_id": 12, "vet_id": 3, "start_at": "2041-01-07T10:15:00Z"}` to `/appointments`
- **THEN** the response status is 422 and the response body contains no `id` of a created appointment

#### Scenario: Scheduling before the opening hours

- **WHEN** an authenticated client posts `{"pet_id": 12, "vet_id": 3, "start_at": "2041-01-07T08:30:00Z"}` to `/appointments`
- **THEN** the response status is 422 and the response body contains no `id` of a created appointment

#### Scenario: Scheduling after the last allowed start

- **WHEN** an authenticated client posts `{"pet_id": 12, "vet_id": 3, "start_at": "2041-01-07T18:00:00Z"}` to `/appointments`
- **THEN** the response status is 422 and the response body contains no `id` of a created appointment

#### Scenario: Scheduling on the last allowed start of the day

- **WHEN** an authenticated client posts `{"pet_id": 12, "vet_id": 3, "start_at": "2041-01-07T17:30:00Z"}` to `/appointments`
- **THEN** the response status is 201 and the body contains `start_at` equal to `2041-01-07T17:30:00Z` and `end_at` equal to `2041-01-07T18:00:00Z`

### Requirement: Appointments cannot start in the past

The service SHALL answer HTTP 422 when `POST /appointments` receives a `start_at` earlier than the current moment, and SHALL NOT create the appointment.

#### Scenario: Scheduling a past date

- **WHEN** an authenticated client posts `{"pet_id": 12, "vet_id": 3, "start_at": "2020-01-06T10:00:00Z"}` to `/appointments`
- **THEN** the response status is 422 and the response body contains no `id` of a created appointment

### Requirement: A veterinarian cannot hold two appointments in the same slot

The service SHALL answer HTTP 409 when `POST /appointments` requests a slot for a veterinarian that already has an active appointment overlapping it, and SHALL NOT create the second appointment.

#### Scenario: Booking a slot already taken by the veterinarian

- **WHEN** the veterinarian `3` already has an appointment with status `scheduled` at `2041-01-07T10:00:00Z` and an authenticated client posts `{"pet_id": 12, "vet_id": 3, "start_at": "2041-01-07T10:00:00Z"}` to `/appointments`
- **THEN** the response status is 409 and the response body contains no `id` of a created appointment

### Requirement: Appointment listing is scoped by role

The service SHALL expose `GET /appointments` as an authenticated endpoint that answers HTTP 200 with a JSON array containing, for a user with role `client`, only the appointments of that client's own pets, and for a user with role `vet`, only the appointments where that user is the veterinarian.

#### Scenario: A client lists the appointments of their pets

- **WHEN** an authenticated client performs `GET /appointments` and the appointments of the clinic are one for pet `12` of that client, one for pet `34` of another client and one where the client is the veterinarian
- **THEN** the response status is 200, the body contains the appointment for pet `12` and does not contain the appointment for pet `34` nor the appointment where the client is the veterinarian

#### Scenario: A veterinarian lists their appointments

- **WHEN** an authenticated user with role `vet` performs `GET /appointments` and the appointments of the clinic include one where that user is the veterinarian and others where they are not
- **THEN** the response status is 200 and the body contains only the appointment where that user is the veterinarian

#### Scenario: Listing appointments without a token

- **WHEN** a client performs `GET /appointments` without an `Authorization` header
- **THEN** the response status is 401 and the response body contains no JSON array of appointments

### Requirement: The pet owner or the veterinarian can cancel an appointment

The service SHALL expose `POST /appointments/{id}/cancel`, SHALL allow the call only for the client that owns the pet of the appointment or for the veterinarian of that appointment, and SHALL answer HTTP 200 with the appointment representation whose `status` is `cancelled`.

#### Scenario: The owner cancels their appointment

- **WHEN** the client that owns the pet of appointment `55` performs `POST /appointments/55/cancel`
- **THEN** the response status is 200 and the body contains `id` equal to `55` and `status` equal to `cancelled`

#### Scenario: The veterinarian cancels their appointment

- **WHEN** the veterinarian of appointment `55` performs `POST /appointments/55/cancel`
- **THEN** the response status is 200 and the body contains `id` equal to `55` and `status` equal to `cancelled`

#### Scenario: An unrelated user tries to cancel

- **WHEN** a user who neither owns the pet of appointment `55` nor is its veterinarian performs `POST /appointments/55/cancel`
- **THEN** the response status is 403 and the body does not contain `status` equal to `cancelled`

### Requirement: Cancelling an unknown appointment is reported as not found

The service SHALL answer HTTP 404 when `POST /appointments/{id}/cancel` is called with an identifier that does not match any appointment.

#### Scenario: Cancelling an appointment that does not exist

- **WHEN** an authenticated client performs `POST /appointments/999999/cancel`
- **THEN** the response status is 404 and the body does not contain `status` equal to `cancelled`

### Requirement: An appointment cannot be cancelled twice

The service SHALL answer HTTP 409 when `POST /appointments/{id}/cancel` is called for an appointment whose `status` is already `cancelled`.

#### Scenario: Cancelling an already cancelled appointment

- **WHEN** an appointment has `status` equal to `cancelled` and its owner performs `POST /appointments/{id}/cancel` again
- **THEN** the response status is 409 and the body does not contain `status` equal to `cancelled`

### Requirement: A cancelled slot becomes available again

The service SHALL treat a cancelled appointment as free, so that the same veterinarian can be booked again in the same slot once the previous appointment has been cancelled.

#### Scenario: Booking a slot freed by a cancellation

- **WHEN** the veterinarian `3` has an appointment with status `cancelled` at `2041-01-07T10:00:00Z` and an authenticated client posts `{"pet_id": 12, "vet_id": 3, "start_at": "2041-01-07T10:00:00Z"}` to `/appointments`
- **THEN** the response status is 201 and the body contains `start_at` equal to `2041-01-07T10:00:00Z` and `status` equal to `scheduled`


<!-- specs/container-runtime/spec.md -->
# Spec Delta

## Purpose

Permite ejecutar de forma reproducible la API de la clínica veterinaria y su base de datos PostgreSQL en cualquier entorno, mediante contenedores declarados en la raíz del repositorio.

## ADDED Requirements

### Requirement: The project is containerized at the repository root

The repository SHALL provide a `Dockerfile` at its root that builds the application image and whose default command runs the API server, and SHALL provide a `docker-compose.yml` at its root that builds that image and runs the application together with a PostgreSQL database.

#### Scenario: Container files are present in the repository root

- **WHEN** a developer lists the root of the repository
- **THEN** a `Dockerfile` and a `docker-compose.yml` are present there

#### Scenario: Compose runs the API together with PostgreSQL

- **WHEN** a developer reviews the root `docker-compose.yml`
- **THEN** it defines an application service built from the root `Dockerfile`, a PostgreSQL service, and the application service receives the database connection settings of that PostgreSQL service


<!-- specs/pets/spec.md -->
# Spec Delta

## Purpose

Permite que un cliente registre las mascotas que atiende y consulte su propia lista, siendo la base sobre la que se agendan los turnos de la clínica.

## ADDED Requirements

### Requirement: Client registers a pet

The service SHALL expose `POST /pets` accepting `name`, `species` and `birth_date`, SHALL bind the new pet to the authenticated client as its owner, and SHALL answer HTTP 201 with the JSON body `{"id": ..., "name": ..., "species": ..., "birth_date": ..., "owner_id": ...}`.

#### Scenario: Registering a pet

- **WHEN** an authenticated client with id `7` posts `{"name": "Firulais", "species": "dog", "birth_date": "2020-05-10"}` to `/pets`
- **THEN** the response status is 201 and the body contains a non-empty `id`, `name` equal to `Firulais`, `species` equal to `dog`, `birth_date` equal to `2020-05-10` and `owner_id` equal to `7`

#### Scenario: Registering a pet with each allowed species

- **WHEN** an authenticated client posts one pet with `species` equal to `dog`, one with `species` equal to `cat` and one with `species` equal to `other`
- **THEN** each of the three requests answers HTTP 201 and each response echoes back the `species` value that was submitted

### Requirement: Only clients may register pets

The service SHALL answer HTTP 403 when `POST /pets` is called by an authenticated user whose role is `vet`, and SHALL NOT create the pet.

#### Scenario: A veterinarian tries to register a pet

- **WHEN** an authenticated user with role `vet` posts `{"name": "Firulais", "species": "dog", "birth_date": "2020-05-10"}` to `/pets`
- **THEN** the response status is 403 and the response body contains no `id` of a created pet

### Requirement: Unknown species are rejected

The service SHALL accept only the species `dog`, `cat` and `other` in `POST /pets`, and SHALL answer HTTP 422 for any other value.

#### Scenario: Registering a pet with a species outside the allowed set

- **WHEN** an authenticated client posts `{"name": "Firulais", "species": "hamster", "birth_date": "2020-05-10"}` to `/pets`
- **THEN** the response status is 422 and no pet is created

### Requirement: Future birth dates are rejected

The service SHALL answer HTTP 422 when `POST /pets` is called with a `birth_date` later than the current date, and SHALL NOT create the pet.

#### Scenario: Registering a pet born in the future

- **WHEN** an authenticated client posts `{"name": "Firulais", "species": "dog", "birth_date": "2999-01-01"}` to `/pets`
- **THEN** the response status is 422 and no pet is created

### Requirement: Pet listing is limited to the authenticated client

The service SHALL expose `GET /pets` as an authenticated endpoint that answers HTTP 200 with a JSON array containing only the pets whose owner is the authenticated user.

#### Scenario: Listing the pets of the authenticated client

- **WHEN** an authenticated client that owns `Firulais` and `Michi` performs `GET /pets` while another client owns `Rex`
- **THEN** the response status is 200, the body contains `Firulais` and `Michi` and does not contain `Rex`

#### Scenario: Listing pets without a token

- **WHEN** a client performs `GET /pets` without an `Authorization` header
- **THEN** the response status is 401 and the response body contains no JSON array of pets


<!-- specs/service-health/spec.md -->
# Spec Delta

## Purpose

Expone una comprobación pública de disponibilidad de la API de la clínica veterinaria, para que el equipo pueda verificar que el servicio está en línea sin autenticarse.

## ADDED Requirements

### Requirement: Public health check

The service SHALL expose `GET /health` as a public endpoint that does not require an `Authorization` header, and SHALL answer HTTP 200 with the JSON body `{"status": "ok"}`.

#### Scenario: Health check without credentials

- **WHEN** a client performs `GET /health` without an `Authorization` header
- **THEN** the response status is 200 and the response body is exactly `{"status": "ok"}`

#### Scenario: Health check ignores an invalid bearer token

- **WHEN** a client performs `GET /health` with an `Authorization: Bearer not-a-valid-token` header
- **THEN** the response status is 200 and the response body is exactly `{"status": "ok"}`


<!-- specs/user-auth/spec.md -->
# Spec Delta

## Purpose

Cubre el alta de usuarios de la clínica (clientes y veterinarios), el inicio de sesión que emite un JWT y la exigencia de un token Bearer en todos los endpoints protegidos de la API.

## ADDED Requirements

### Requirement: User registration

The service SHALL expose `POST /auth/register` accepting `email`, `password` and `role`, SHALL create the user with the requested role and SHALL answer HTTP 201 with the JSON body `{"id": ..., "email": ..., "role": ...}` without exposing the password.

#### Scenario: Register a client account

- **WHEN** an unauthenticated client posts `{"email": "ana@example.com", "password": "clinic2024", "role": "client"}` to `/auth/register`
- **THEN** the response status is 201 and the body contains `email` equal to `ana@example.com`, `role` equal to `client` and a non-empty `id`, with no `password` field

#### Scenario: Register a veterinarian account

- **WHEN** an unauthenticated client posts `{"email": "dr.vega@example.com", "password": "clinic2024", "role": "vet"}` to `/auth/register`
- **THEN** the response status is 201 and the body contains `email` equal to `dr.vega@example.com`, `role` equal to `vet` and a non-empty `id`, with no `password` field

### Requirement: Duplicate email is rejected

The service SHALL answer HTTP 409 when `POST /auth/register` is called with an `email` that is already registered, and SHALL NOT create a second account for it.

#### Scenario: Registering an existing email

- **WHEN** an unauthenticated client posts `{"email": "ana@example.com", "password": "clinic2024", "role": "client"}` to `/auth/register` and `ana@example.com` is already registered
- **THEN** the response status is 409 and the response body does not contain the fields `id`, `email` or `role`

### Requirement: Short passwords are rejected

The service SHALL answer HTTP 422 when `POST /auth/register` is called with a `password` shorter than 8 characters, and SHALL NOT create the account.

#### Scenario: Registering with a password under 8 characters

- **WHEN** an unauthenticated client posts `{"email": "ana@example.com", "password": "abc1234", "role": "client"}` to `/auth/register`
- **THEN** the response status is 422 and no account is created for `ana@example.com`

### Requirement: Unknown roles are rejected

The service SHALL accept only the roles `client` and `vet` in `POST /auth/register`, and SHALL answer HTTP 422 for any other role value.

#### Scenario: Registering with a role outside the allowed set

- **WHEN** an unauthenticated client posts `{"email": "ana@example.com", "password": "clinic2024", "role": "admin"}` to `/auth/register`
- **THEN** the response status is 422 and no account is created for `ana@example.com`

### Requirement: Login issues a bearer JWT

The service SHALL expose `POST /auth/login` accepting `email` and `password`, and on success SHALL answer HTTP 200 with the JSON body `{"access_token": ..., "token_type": "bearer"}` where `access_token` is a JWT.

#### Scenario: Successful login

- **WHEN** an unauthenticated client posts `{"email": "ana@example.com", "password": "clinic2024"}` to `/auth/login` for an existing account
- **THEN** the response status is 200, the body contains `token_type` equal to `bearer` and a non-empty `access_token` made of three dot-separated JWT segments whose payload carries the user id and role

### Requirement: Invalid credentials are rejected

The service SHALL answer HTTP 401 when `POST /auth/login` receives credentials that do not match a registered account, without revealing whether the email exists.

#### Scenario: Login with a wrong password

- **WHEN** an unauthenticated client posts `{"email": "ana@example.com", "password": "wrongpass"}` to `/auth/login`
- **THEN** the response status is 401 and the body contains no `access_token`

#### Scenario: Login with an unknown email

- **WHEN** an unauthenticated client posts `{"email": "nobody@example.com", "password": "clinic2024"}` to `/auth/login`
- **THEN** the response status is 401 and the body contains no `access_token`

### Requirement: Protected endpoints require a bearer token

Every endpoint other than `GET /health`, `POST /auth/register` and `POST /auth/login` SHALL require an `Authorization: Bearer <jwt>` header, and SHALL answer HTTP 401 when that header is missing or the token is not a valid, unexpired JWT issued by the service.

#### Scenario: Protected endpoint called without an Authorization header

- **WHEN** a client performs `GET /vets` without an `Authorization` header
- **THEN** the response status is 401 and the response body contains no list of veterinarians

#### Scenario: Protected endpoint called with a malformed token

- **WHEN** a client performs `GET /pets` with the header `Authorization: Bearer not-a-jwt`
- **THEN** the response status is 401 and the response body contains no list of pets

#### Scenario: Protected endpoint called with a token signed with another secret

- **WHEN** a client performs `GET /appointments` with a bearer token whose signature was produced with a different secret
- **THEN** the response status is 401 and the response body contains no list of appointments

#### Scenario: Protected endpoint called with an expired token

- **WHEN** a client performs `GET /pets` with a bearer token whose expiration moment has already passed
- **THEN** the response status is 401 and the response body contains no list of pets


<!-- specs/vet-directory/spec.md -->
# Spec Delta

## Purpose

Permite consultar el directorio de veterinarios de la clínica, para que un cliente pueda elegir con qué profesional agendar un turno.

## ADDED Requirements

### Requirement: Veterinarian directory listing

The service SHALL expose `GET /vets` as an authenticated endpoint that answers HTTP 200 with a JSON array listing every account whose role is `vet`, where each element contains exactly the fields `id` and `email`.

#### Scenario: Listing the veterinarians of the clinic

- **WHEN** an authenticated client performs `GET /vets` with a valid bearer token and the clinic has the accounts `dr.vega@example.com` (role `vet`) and `ana@example.com` (role `client`)
- **THEN** the response status is 200, the body is a JSON array, every element has exactly the fields `id` and `email`, `dr.vega@example.com` appears in the array and `ana@example.com` does not appear in the array

#### Scenario: Listing the veterinarians without a token

- **WHEN** a client performs `GET /vets` without an `Authorization` header
- **THEN** the response status is 401 and the response body contains no JSON array of veterinarians


# Design

## Context

- The repository is greenfield: only `openspec/` and `.opencode/` exist. There is no Python project, no schema, no container definition and no CI yet. This change creates the whole backend.
- Delivery environment facts that shape the approach (verified in the workspace):
  - Python 3.11 with `fastapi` 0.134, `pydantic` 2.14, `python-jose` 3.5, `bcrypt` 4.1.2, `psycopg` 3.2.10, `httpx` 0.27.2, `pytest` 9.0.3 and `uvicorn` 0.31.1 preinstalled in `/venv`; `pip` installs from the network are possible.
  - **No Docker daemon**, so `docker build` / `docker compose up` cannot run here; container files are authored and checked statically.
  - **No local PostgreSQL server** and no root to install one, so the automated suite cannot depend on a PostgreSQL instance.
- Product constraints: the API is used only by the internal clinic team; a single Developer agent writes the code and the tests (no QA, no DevSec).
- Motivation is in `proposal.md`; the behaviour contract is in `specs/`. This document only explains how.

## Goals / Non-Goals

**Goals:**

- One FastAPI application serving exactly the seven documented routes (`/health`, `/auth/register`, `/auth/login`, `/vets`, `/pets`, `/appointments`, `/appointments/{id}/cancel`) over PostgreSQL.
- One declarative ORM model that behaves identically on the production backend (PostgreSQL) and on the backend used by the automated suite (SQLite), so the suite verifies behaviour without a database server.
- Deterministic, isolated slot rules (weekday, minutes, opening hours, past dates) implemented as pure functions, independent of HTTP and of the database.
- Explicit mapping from domain failures to the exact status codes fixed by the specs (401, 403, 404, 409, 422).
- A reproducible container runtime: `Dockerfile` + `docker-compose.yml` at the repository root.

**Non-Goals:**

- No web frontend, no admin/back-office panel, no internal admin role.
- No notifications, no e-mail, no reminders, no recurring appointments.
- No pagination, search, filtering or sorting on list endpoints; no soft delete; no audit trail.
- No refresh tokens, no sessions, no logout endpoint, no password reset, no email verification.
- No multi-clinic/tenant model, no availability templates, no holidays calendar, no vet specialisation, no per-vet working-hours configuration (the opening-hours grid is global).
- No pet attributes beyond `name`, `species`, `birth_date` (no breed, weight, medical history, photo).
- No appointment notes, no rescheduling (cancel + create), no recurring slots.
- No migration tooling (Alembic) in this first delivery, no observability stack, no rate limiting, no CORS policy.

## Decisions

### D1. Layout: `app/` package with `routers/`, `services/` and `tests/` at the root

The application lives in `app/` with one module per concern and a flat `tests/` package mirroring the HTTP surface.

*Alternative considered:* a `src/` layout with a packaged distribution. Rejected — nothing needs to be published and it adds packaging metadata to a single-service repo.

### D2. Synchronous SQLAlchemy 2.0 over `psycopg` (v3)

Endpoints are plain `def` handlers (FastAPI runs them in its worker threadpool) with a request-scoped session from `app/database.py`. The PostgreSQL URL uses the `postgresql+psycopg://` driver.

*Alternative considered:* `async` SQLAlchemy + `asyncpg`. Rejected for v1: it adds an event-loop-bound session model and a second driver dependency for no measurable gain at the clinic's scale.

### D3. Same ORM model on PostgreSQL (runtime) and SQLite (automated suite)

There is no PostgreSQL server available in the delivery environment, so the suite runs against an in-memory SQLite database while the containerised runtime uses PostgreSQL. To keep both honest, the model layer is restricted to portable constructs:

- `id`: `Integer` primary key with autoincrement (no server sequence).
- `email`: `String` with a unique index (no case-insensitive collation; the application normalises before comparing).
- `role`, `species`, `status`: `String` columns, validated by the schema layer, never by a database enum (native enums do not exist in SQLite).
- `birth_date`: `Date`.
- `start_at`, `end_at`: `DateTime(timezone=True)` through a `UTCDateTime` type decorator (`app/models.py`) that normalises to UTC on write and re-attaches `tzinfo=UTC` on read, so a value read back from SQLite is identical to one read back from PostgreSQL.
- No PostgreSQL-only types, no `ARRAY`, no `JSONB`, no partial-index-only features except the one partial index in D10, which both engines support.

*Alternative considered:* requiring PostgreSQL for the suite and skipping it otherwise. Rejected — a suite that cannot run is not a verification; the portability constraints above are the mitigation for the resulting behavioural gap.

### D4. Schema created at startup with `Base.metadata.create_all`

`app/database.py` creates the tables on application startup (`app/main.py` lifespan). There is no migration history to preserve at initial delivery.

*Alternative considered:* Alembic from day one. Rejected for v1 as out-of-scope tooling; the trade-off is recorded in Risks and the migration story for the next schema change.

### D5. Authentication: HS256 JWT in a Bearer header

- Token payload: `sub` (user id as string), `role`, `iat`, `exp`; algorithm `HS256`; secret from the `JWT_SECRET` environment variable; access-token lifetime 60 minutes.
- `app/dependencies.py` exposes `get_current_user`, which decodes the token, verifies the signature and the expiry, loads the user by `sub` and raises `401` (with `WWW-Authenticate: Bearer`) for every failure mode: missing header, malformed token, wrong signature, expired token, unknown user.
- Every protected route declares `current_user: User = Depends(get_current_user)`; `GET /health`, `POST /auth/register` and `POST /auth/login` declare no such dependency, so they stay public.
- The router and the dependency ignore an `Authorization` header that is not a `Bearer` scheme the same way as an invalid token: both produce `401`.

*Alternative considered:* opaque session tokens in the database. Rejected — the request explicitly asks for a JWT.

### D6. Password hashing with PBKDF2-HMAC-SHA256 from the standard library

`app/security.py` derives the hash with `hashlib.pbkdf2_hmac("sha256", ...)` using a per-user random 16-byte salt and 200 000 iterations, stored as `pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>`. Verification is constant-time via `hmac.compare_digest`.

*Alternative considered:* `passlib` + `bcrypt`. Rejected — `passlib` is unmaintained and `bcrypt` 4.x raises on inputs longer than 72 bytes, which would turn a long password into a `500`; PBKDF2 has no length limit and adds no dependency. The algorithm choice is invisible to the specs and can be swapped later by keeping the stored-format prefix.

### D7. Validation split: shape rules in the schemas, business rules in the services

- Schema layer (`app/schemas.py`, Pydantic v2) fixes the shape of the contract: `role` as `Literal["client", "vet"]`, `species` as `Literal["dog", "cat", "other"]`, `password` with `min_length=8`, `birth_date` with a validator rejecting a date later than today. Any of these failures surfaces as FastAPI's native `422`.
- Business rules live in `app/services/` and raise the domain errors of `app/errors.py`; `app/main.py` registers exception handlers that translate them into `403`, `404` and `409` responses with a `{"detail": ...}` body.

*Alternative considered:* a single middleware that maps every failure. Rejected — per-endpoint raises keep the rules close to the behaviour and keep the response bodies predictable.

### D8. Email identity is the normalised address

`email` is a plain `String`; the application stores `email.strip().lower()` and the uniqueness constraint is enforced by a unique index plus an explicit pre-check, so a repeated registration answers `409` (not `422`, not a `500` on the integrity error). No `EmailStr` and no `email-validator` dependency: the request does not ask for address-format validation, and adding it would reject inputs the specs do not forbid.

*Alternative considered:* `pydantic[email]` with `EmailStr`. Rejected — it introduces a `422` the specs never describe.

### D9. Slot rules are pure functions over UTC datetimes

`app/services/scheduling.py` exposes:

- `parse_start_at(raw)` → timezone-aware UTC `datetime`; a naive or non-ISO-8601 value is rejected as `422`.
- `validate_slot(start_at, now)` → the ordered list of violated rules among: *not in the past*, *weekday is Monday–Saturday*, *minutes are `00` or `30`*, *start time is between `09:00` and `17:30` UTC inclusive*.
- `slot_end(start_at)` → `start_at + 30 minutes`.

The rules are evaluated against the UTC wall clock, because `start_at` is defined as UTC. The functions never touch the database or the request, which keeps them unit-testable in isolation.

*Alternative considered:* expressing the grid as a cron/recurrence library. Rejected — the grid is a fixed half-hourly pattern inside a fixed daily window; plain comparisons are clearer.

### D10. Conflicts are detected by interval overlap on the veterinarian's active appointments

A slot is taken when the veterinarian has an appointment with `status = "scheduled"` whose `[start_at, end_at)` interval intersects the requested `[start_at, start_at + 30min)` interval. Because every appointment is 30 minutes long and starts on `00`/`30`, the only intersecting case in practice is the same start, but the interval test is written generally so the rule stays correct if durations change.

`cancelled` appointments are excluded from the overlap query, which is what frees the slot for a new booking.

In addition, `app/models.py` declares a partial unique index over `(vet_id, start_at)` restricted to rows with `status = "scheduled"`, expressed for both dialects (`sqlite_where` / `postgresql_where`). The database therefore refuses a double booking even if two requests race past the overlap check; the application maps that integrity error to `409` as well.

*Alternative considered:* checking conflicts only in application code. Rejected — it is not race-safe.

### D11. Authorisation is resolved in a fixed order

`POST /appointments` evaluates its checks in this order, so the status code never depends on how many things are wrong at once: authenticated (`401`) → role is `client` (`403`) → the pet exists (`404`) → the pet belongs to the caller (`403`) → the veterinarian exists (`404`) → the slot is valid (`422`) → the veterinarian is free (`409`) → create (`201`). Existence is therefore checked before ownership, which is what makes "unknown pet" (`404`) and "someone else's pet" (`403`) distinguishable.

`POST /appointments/{id}/cancel` evaluates: authenticated (`401`) → the appointment exists (`404`) → the caller owns the pet or is the veterinarian (`403`) → it is not already `cancelled` (`409`) → cancel (`200`).

### D12. Response bodies are exactly the documented shapes

`app/schemas.py` defines one response model per endpoint, so the JSON keys are fixed: user `{"id", "email", "role"}`; pet `{"id", "name", "species", "birth_date", "owner_id"}`; appointment `{"id", "pet_id", "vet_id", "start_at", "end_at", "status"}`; veterinarian `{"id", "email"}`; login `{"access_token", "token_type"}`; health `{"status"}`. Password hashes and internal columns are never serialised. `start_at` and `end_at` are rendered as UTC ISO 8601 strings.

### D13. The container runtime is PostgreSQL + the API, on port 8000

`Dockerfile` (root) is a `python:3.11-slim` image that installs `requirements.txt`, copies the `app/` package and starts `uvicorn app.main:app --host 0.0.0.0 --port 8000`. `docker-compose.yml` (root) defines the `api` service built from that Dockerfile plus a `db` service running `postgres:16-alpine` with a named volume, a `pg_isready` healthcheck and `depends_on: {db: {condition: service_healthy}}`; the API receives `DATABASE_URL` and `JWT_SECRET` from the environment. The published port is `8000`; the port `8202` is never used by any file in this repository.

*Alternative considered:* `compose.yaml` (the new Compose spelling). Rejected — the requirement names `docker-compose.yml` explicitly.

### D14. The suite exercises behaviour only, and never needs Docker

`tests/` uses `pytest` with FastAPI's `TestClient` (httpx). `tests/conftest.py` builds an isolated in-memory SQLite engine per test session, creates the schema, overrides the database dependency and exposes fixtures for an anonymous client, a registered client, a registered veterinarian, a pet owned by the client and the corresponding `Authorization` headers.

Two consequences are deliberate:

- **Dates are computed, not hard-coded.** The literal dates in the specs (for example `2041-01-07T10:00:00Z`) illustrate the format and the boundaries; the suite derives a *future* Monday at the same clock time so that no test expires, and it derives a *future* Sunday for the weekday rule so that the `422` is attributable to the weekday and not to the past-date rule.
- **No test reads `Dockerfile`, `docker-compose.yml`, `README.md` or any script.** The container files are reviewed statically instead (see the tasks), and the API behaviour that matters is covered through the HTTP endpoints.

### D15. Files to create

```
/requirements.txt              pinned runtime + test dependencies
/pyproject.toml                project metadata and pytest configuration
/Dockerfile                    image that builds and runs the API
/docker-compose.yml            api service + postgres service, wired together
/README.md                     how to run it and curl examples for every endpoint
/.dockerignore                 build context exclusions
/app/__init__.py               package marker
/app/main.py                   application factory, router wiring, exception handlers, startup schema creation
/app/config.py                 environment-driven settings (DATABASE_URL, JWT_SECRET, token lifetime)
/app/database.py               engine, session factory, Base, get_db dependency
/app/models.py                 User, Pet, Appointment and the UTCDateTime decorator and indexes
/app/schemas.py                request and response models for every endpoint
/app/security.py               password hashing and verification, JWT encode/decode
/app/dependencies.py           get_current_user Bearer dependency
/app/errors.py                 domain errors and their HTTP status mapping
/app/routers/__init__.py       package marker
/app/routers/health.py         GET /health
/app/routers/auth.py           POST /auth/register, POST /auth/login
/app/routers/vets.py           GET /vets
/app/routers/pets.py           POST /pets, GET /pets
/app/routers/appointments.py   POST /appointments, GET /appointments, POST /appointments/{id}/cancel
/app/services/__init__.py      package marker
/app/services/users.py         user creation, duplicate check, credential verification, vet listing
/app/services/pets.py          pet creation and owner listing
/app/services/scheduling.py    pure slot rules (parse, validate, end time)
/app/services/appointments.py  slot availability, appointment creation, role-scoped listing, cancellation
/tests/__init__.py             package marker
/tests/conftest.py             engine/schema fixtures, user and pet factories, auth headers
/tests/test_models.py          persistence behaviour: schema creation, UTC round-trip, uniqueness constraints
/tests/test_security.py        password hashing and JWT encoding/decoding unit tests
/tests/test_scheduling.py      pure slot-rule unit tests (weekday, minutes, opening hours, past dates)
/tests/test_health.py          health endpoint
/tests/test_auth.py            register and login, duplicate email, weak password, invalid role, bad credentials, bearer enforcement
/tests/test_vets.py            veterinarian directory listing
/tests/test_pets.py            pet creation, role restriction, species and birth_date validation, owner-scoped listing
/tests/test_appointments.py    scheduling, slot rules, ownership and existence rules, conflicts, listing by role, cancellation
```

## Risks / Trade-offs

- **The suite runs on SQLite while production runs on PostgreSQL** → the ORM layer is restricted to portable column types and the `UTCDateTime` decorator normalises both sides to UTC; no PostgreSQL-only feature is used, and the D10 partial index is declared for both dialects. A residual gap remains in exotic type coercion, which is why the API contract is expressed in plain strings, integers, dates and ISO 8601 timestamps.
- **No migration tooling** → the schema is created from the models on startup; the first schema change will require introducing Alembic, and the models are kept declarative to make that migration cheap. Data is disposable at this stage, so no backfill is needed now.
- **The email uniqueness relies on application normalisation plus a unique index** → concurrent registrations of the same normalised address are resolved by catching the integrity error and answering `409` instead of `500`.
- **The double-booking guarantee depends on the partial unique index being present in the production database** → it is declared in the model metadata, so `create_all` applies it in both engines; the application also checks the overlap explicitly to return a friendly `409`.
- **A fixed global opening-hours grid with no holidays** → out of scope by design; the rules are isolated in `app/services/scheduling.py` so a per-vet schedule or a holidays table can be added there without touching the routers.
- **A 60-minute token lifetime forces a re-login** → acceptable for an internal tool; refresh tokens are out of scope.
- **No rate limiting or audit trail** → acceptable for an internal clinic team on a private network; it is listed as a non-goal, not an oversight.
- **The literal example dates in the specs eventually fall in the past** → the suite computes its dates, so the suite stays green; the specs are read as illustrations of the format and boundaries.

## Migration Plan

- Nothing to migrate: this is the first delivery and there is no data, no user base and no previous schema.
- Deployment is the container runtime: the image is built from the root `Dockerfile` and started together with PostgreSQL through the root `docker-compose.yml`; the schema is created automatically on the first API start, and the database lives in a named volume so restarts keep the data.
- Rollback is a redeploy of the previous image and, if required, removal of the database volume. Nothing outside the container images and the database volume is touched, so a rollback cannot affect other systems.
- The image is not built or run in this delivery environment: there is no Docker daemon here, so `Dockerfile` and `docker-compose.yml` are verified statically (the Compose file parses as YAML, every `COPY` source path exists in the repository, the service wiring matches the documented environment variables) and exercised later wherever a daemon is available.

## Open Questions

None that affect the specs, the approach or the task breakdown. The following minor decisions are recorded here so they can be revisited without reopening the design: access-token lifetime (60 minutes), PBKDF2 iteration count (200 000), PostgreSQL major version (16) and the SQLite-in-suite backend.
