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
