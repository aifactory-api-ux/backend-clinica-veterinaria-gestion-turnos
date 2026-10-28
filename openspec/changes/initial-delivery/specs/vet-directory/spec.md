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
