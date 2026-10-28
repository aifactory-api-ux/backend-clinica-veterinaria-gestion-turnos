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
