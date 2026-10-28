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
