# Imagen de la API de la clínica veterinaria.
FROM python:3.11-slim

# Evita escribir bytecode y deja la salida sin búfer para que los registros
# del contenedor aparezcan de inmediato en `docker compose logs`.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /srv/clinica

# Las dependencias se instalan en una capa propia: se resuelven antes de
# copiar el código, de modo que un cambio en `app/` no reinstala nada.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Solo se copia el paquete de la aplicación; el resto del repositorio no
# forma parte de la imagen.
COPY app/ ./app/

# La API se ejecuta como un usuario sin permisos elevados: el proceso no
# necesita privilegios para atender las peticiones.
RUN useradd --create-home --uid 10001 clinica
USER clinica

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
