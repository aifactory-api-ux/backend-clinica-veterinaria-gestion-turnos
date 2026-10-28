# API de la clínica veterinaria

Backend REST de la clínica veterinaria: alta de usuarios (clientes y veterinarios),
registro de mascotas y gestión de turnos con control de franja horaria y de
solapamientos por veterinario.

## Requisitos

- Python 3.11 o superior.
- PostgreSQL 16 para el runtime con contenedores; para el desarrollo local basta el
  SQLite que ya viene incluido en Python.
- `venv` y `pip` del propio Python.
- Docker con el plugin Compose v2, para ejecutar el stack con contenedores.

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Variables de entorno

| Variable | Obligatoria | Valor por defecto | Descripción |
| --- | --- | --- | --- |
| `DATABASE_URL` | No | `sqlite:///./clinica.db` | Cadena de conexión de SQLAlchemy. |
| `JWT_SECRET` | No | `dev-secret-change-me` | Clave con la que se firman los tokens JWT. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `60` | Vigencia del token de acceso, en minutos. |

La clave por defecto sirve únicamente para el desarrollo local: en cualquier entorno
compartido hay que fijar una propia, por ejemplo:

```bash
export JWT_SECRET="una-clave-secreta"
```

## Ejecución local

```bash
export DATABASE_URL="sqlite:///./clinica.db"
export JWT_SECRET="una-clave-secreta"
uvicorn app.main:app --port 8000
```

La API queda disponible en `http://127.0.0.1:8000` y su documentación interactiva en
`http://127.0.0.1:8000/docs`.

## Ejecución con Docker Compose

El `docker-compose.yml` de la raíz levanta el stack completo: el servicio `api`,
construido a partir del `Dockerfile` de la raíz, y el servicio `db`, un PostgreSQL
16 cuyos datos quedan en el volumen con nombre `postgres_data`. El servicio `api`
no arranca hasta que `db` supera su healthcheck `pg_isready`, y crea el esquema
de la base de datos en su primer arranque.

```bash
# Construye la imagen de la API
docker compose build

# Levanta la API y la base de datos en segundo plano
docker compose up -d

# Sigue los registros de los dos servicios
docker compose logs -f

# Detiene el stack conservando los datos
docker compose down

# Detiene el stack y borra además el volumen de PostgreSQL
docker compose down -v
```

La API queda publicada en `http://127.0.0.1:8000` —el puerto `8000` del host
mapeado al `8000` del contenedor— y su documentación interactiva en
`http://127.0.0.1:8000/docs`.

### Variables de entorno del stack

| Variable | Obligatoria | Valor por defecto | Descripción |
| --- | --- | --- | --- |
| `JWT_SECRET` | No | `dev-secret-change-me` | Clave con la que la API firma los tokens JWT. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `60` | Vigencia del token de acceso, en minutos. |

`DATABASE_URL` no se fija a mano: el servicio `api` la recibe ya apuntando al
servicio `db` del compose
(`postgresql+psycopg://clinica:clinica@db:5432/clinica`). Para usar una clave
propia, se exporta antes de levantar el stack:

```bash
export JWT_SECRET="una-clave-secreta"
docker compose up -d
```

Compose también lee un archivo `.env` en la raíz del repositorio —ignorado por
Git— donde se pueden fijar esas mismas variables sin exportarlas de antemano.

## Comprobación de estado

`GET /health` es público: no exige cabecera `Authorization`, de modo que sirve tanto
para verificar que la API está en marcha como para comprobar su salud desde un
balanceador o un sistema de monitorización.

```bash
curl -i http://127.0.0.1:8000/health
```

Respuesta:

```
HTTP/1.1 200 OK
content-type: application/json

{"status":"ok"}
```

## Registro de cuentas

`POST /auth/register` es público: da de alta una cuenta de cliente o de
veterinario. El `role` solo admite `client` y `vet` y la contraseña debe tener
al menos 8 caracteres. El email es la identidad de la cuenta: se normaliza
(minúsculas y sin espacios) y no puede repetirse.

```bash
curl -i -X POST http://127.0.0.1:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "ana@example.com", "password": "clinic2024", "role": "client"}'
```

Respuesta:

```
HTTP/1.1 201 Created
content-type: application/json

{"id":1,"email":"ana@example.com","role":"client"}
```

La contraseña nunca se devuelve. Un email ya registrado responde `409`:

```
HTTP/1.1 409 Conflict
content-type: application/json

{"detail":"El email ya está registrado."}
```

Una contraseña de menos de 8 caracteres o un `role` distinto de `client` y `vet`
responden `422`, con el detalle del campo que incumple las reglas.

## Inicio de sesión

`POST /auth/login` es público y valida las credenciales de una cuenta existente.
Si son correctas, devuelve un token JWT de acceso con una vigencia de 60
minutos.

```bash
curl -i -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "ana@example.com", "password": "clinic2024"}'
```

Respuesta:

```
HTTP/1.1 200 OK
content-type: application/json

{"access_token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwicm9sZSI6ImNsaWVudCJ9.firma","token_type":"bearer"}
```

Si el email no está registrado o la contraseña no coincide, la respuesta es
`401` y no incluye `access_token`:

```
HTTP/1.1 401 Unauthorized
content-type: application/json

{"detail":"Credenciales inválidas."}
```

## Uso del token Bearer

Todos los endpoints salvo `GET /health`, `POST /auth/register` y
`POST /auth/login` exigen la cabecera `Authorization: Bearer <token>`. Sin
cabecera, o con un token mal formado, firmado con otra clave o ya caducado, la
respuesta es `401`.

```bash
TOKEN="<access_token devuelto por /auth/login>"

curl -i http://127.0.0.1:8000/vets \
  -H "Authorization: Bearer $TOKEN"
```

La misma cabecera acompaña a todas las peticiones a los endpoints protegidos
de la API.

## Directorio de veterinarios

`GET /vets` devuelve los veterinarios de la clínica, para que un cliente pueda
elegir con qué profesional agendar un turno. Es un endpoint protegido: exige
la cabecera `Authorization: Bearer <token>` y, sin ella o con un token
inválido, responde `401`.

```bash
curl -i http://127.0.0.1:8000/vets \
  -H "Authorization: Bearer $TOKEN"
```

Respuesta:

```
HTTP/1.1 200 OK
content-type: application/json

[{"id":2,"email":"dr.vega@example.com"}]
```

Cada elemento expone únicamente su `id` y su `email`. Solo aparecen las
cuentas con `role` `vet`: los clientes no forman parte del directorio.

## Registro de mascotas

`POST /pets` da de alta una mascota a nombre del cliente autenticado. Solo los
clientes pueden registrar mascotas: una cuenta con `role` `vet` recibe `403` y
la mascota no se crea. La especie solo admite `dog`, `cat` u `other` y la fecha
de nacimiento no puede ser posterior al día de hoy; en ambos casos la respuesta
es `422`.

```bash
curl -i -X POST http://127.0.0.1:8000/pets \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name": "Firulais", "species": "dog", "birth_date": "2020-05-10"}'
```

Respuesta:

```
HTTP/1.1 201 Created
content-type: application/json

{"id":1,"name":"Firulais","species":"dog","birth_date":"2020-05-10","owner_id":1}
```

El `owner_id` es el identificador del cliente autenticado y la fecha de
nacimiento se devuelve en formato `AAAA-MM-DD`.

Una especie no admitida responde `422` con el detalle del campo que incumple
la regla:

```
HTTP/1.1 422 Unprocessable Entity
content-type: application/json

{"detail":[{"type":"literal_error","loc":["body","species"],"msg":"Input should be 'dog', 'cat' or 'other'","input":"hamster","ctx":{"expected":"'dog', 'cat' or 'other'"}}]}
```

Una fecha de nacimiento futura responde `422` con el detalle del campo que
incumple la regla:

```
HTTP/1.1 422 Unprocessable Entity
content-type: application/json

{"detail":[{"type":"value_error","loc":["body","birth_date"],"msg":"Value error, La fecha de nacimiento no puede ser futura.","input":"2999-01-01","ctx":{"error":{}}}]}
```

Y un veterinario recibe `403`:

```
HTTP/1.1 403 Forbidden
content-type: application/json

{"detail":"Solo los clientes pueden registrar mascotas."}
```

## Listado de mascotas

`GET /pets` devuelve las mascotas del usuario autenticado y solo las suyas: es
un endpoint protegido, así que sin cabecera `Authorization` o con un token
inválido responde `401`.

```bash
curl -i http://127.0.0.1:8000/pets \
  -H "Authorization: Bearer $TOKEN"
```

Respuesta:

```
HTTP/1.1 200 OK
content-type: application/json

[{"id":1,"name":"Firulais","species":"dog","birth_date":"2020-05-10","owner_id":1}]
```

Cada elemento expone únicamente su `id`, `name`, `species`, `birth_date` y
`owner_id`. Un cliente sin mascotas recibe un arreglo vacío.

## Agendar un turno

`POST /appointments` agenda un turno de 30 minutos para una mascota del
cliente autenticado. Solo los clientes pueden agendar: una cuenta con `role`
`vet` recibe `403` y no se crea ningún turno. La petición indica la mascota
(`pet_id`), el veterinario (`vet_id`) y el inicio del turno (`start_at`) en
instante UTC ISO 8601.

```bash
curl -i -X POST http://127.0.0.1:8000/appointments \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"pet_id": 1, "vet_id": 2, "start_at": "2041-01-07T10:00:00Z"}'
```

Respuesta:

```
HTTP/1.1 201 Created
content-type: application/json

{"id":1,"pet_id":1,"vet_id":2,"start_at":"2041-01-07T10:00:00Z","end_at":"2041-01-07T10:30:00Z","status":"scheduled"}
```

El turno dura 30 minutos: `end_at` es `start_at` más media hora. El inicio
solo se admite de lunes a sábado, en punto o en media hora, y entre las
09:00 y las 17:30 (UTC), de modo que el último turno del día empieza a las
17:30 y termina a las 18:00.

Un inicio en el pasado, un domingo, una hora con minutos que no sean 00 o 30
o un inicio fuera de la franja horaria responden `422`:

```
HTTP/1.1 422 Unprocessable Entity
content-type: application/json

{"detail":"El horario solicitado no es válido: el inicio del turno debe ser en punto o en media hora."}
```

Una mascota o un veterinario que no existen responden `404`:

```
HTTP/1.1 404 Not Found
content-type: application/json

{"detail":"El veterinario no existe."}
```

Agendar un turno para una mascota de otro cliente responde `403`, igual que
agendarlo con una cuenta de veterinario:

```
HTTP/1.1 403 Forbidden
content-type: application/json

{"detail":"Solo los clientes pueden agendar turnos."}
```

Y si el veterinario ya tiene un turno activo en ese horario, la respuesta es
`409`:

```
HTTP/1.1 409 Conflict
content-type: application/json

{"detail":"El veterinario ya tiene un turno en ese horario."}
```

## Listado de turnos

`GET /appointments` devuelve los turnos que le corresponden al usuario autenticado y
solo a él: un cliente ve los turnos de sus propias mascotas y un veterinario ve los
turnos en los que atiende. Es un endpoint protegido, así que sin cabecera
`Authorization` o con un token inválido responde `401`.

```bash
curl -i http://127.0.0.1:8000/appointments \
  -H "Authorization: Bearer $TOKEN"
```

Respuesta:

```
HTTP/1.1 200 OK
content-type: application/json

[{"id":1,"pet_id":1,"vet_id":2,"start_at":"2041-01-07T10:00:00Z","end_at":"2041-01-07T10:30:00Z","status":"scheduled"}]
```

Cada elemento expone únicamente `id`, `pet_id`, `vet_id`, `start_at`, `end_at` y
`status`, y el listado viene ordenado por hora de inicio. Un usuario sin turnos
recibe un arreglo vacío.

## Cancelación de un turno

`POST /appointments/{id}/cancel` cancela un turno existente. Solo pueden cancelarlo el
cliente dueño de la mascota y el veterinario que atiende el turno; cualquier otra
cuenta recibe `403` y el turno permanece activo.

```bash
curl -i -X POST http://127.0.0.1:8000/appointments/1/cancel \
  -H "Authorization: Bearer $TOKEN"
```

Respuesta:

```
HTTP/1.1 200 OK
content-type: application/json

{"id":1,"pet_id":1,"vet_id":2,"start_at":"2041-01-07T10:00:00Z","end_at":"2041-01-07T10:30:00Z","status":"cancelled"}
```

El turno se devuelve con su estado actualizado a `cancelled`. Un identificador que no
corresponde a ningún turno responde `404`:

```
HTTP/1.1 404 Not Found
content-type: application/json

{"detail":"El turno no existe."}
```

Una cuenta sin relación con el turno recibe `403`:

```
HTTP/1.1 403 Forbidden
content-type: application/json

{"detail":"Solo el dueño de la mascota o el veterinario del turno pueden cancelarlo."}
```

Y cancelar un turno que ya está cancelado responde `409`:

```
HTTP/1.1 409 Conflict
content-type: application/json

{"detail":"El turno ya está cancelado."}
```

Al cancelar un turno, su horario queda libre: el mismo veterinario puede volver a ser
reservado en ese mismo tramo.

## Estructura del proyecto

```
.
├── app/
│   ├── config.py       Ajustes de ejecución leídos del entorno
│   ├── database.py     Motor, sesión y base declarativa
│   ├── dependencies.py Dependencia de autenticación por token Bearer
│   ├── errors.py       Errores de dominio y su código HTTP equivalente
│   ├── main.py         Punto de entrada ASGI de la aplicación
│   ├── models.py       Modelos User, Pet y Appointment
│   ├── routers/        Rutas HTTP, un módulo por recurso
│   ├── schemas.py      Esquemas de entrada y salida de la API
│   ├── security.py     Hash de contraseñas y emisión de tokens JWT
│   └── services/       Reglas de negocio de la clínica
├── tests/              Pruebas automatizadas
├── .dockerignore       Exclusiones del contexto de construcción de la imagen
├── docker-compose.yml  Stack con la API y PostgreSQL
├── Dockerfile          Imagen que construye y ejecuta la API
├── pyproject.toml      Metadatos del proyecto y configuración de pytest
└── requirements.txt    Dependencias de runtime y de pruebas
```

## Pruebas

```bash
pytest -q
```

La suite se ejecuta contra una base SQLite en memoria, de modo que no necesita un
servidor de PostgreSQL para verificarse.
