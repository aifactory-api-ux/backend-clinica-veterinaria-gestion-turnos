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
