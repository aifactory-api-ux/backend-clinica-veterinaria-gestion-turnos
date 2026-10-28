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
