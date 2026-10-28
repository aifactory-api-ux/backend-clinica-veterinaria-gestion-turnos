"""Pruebas de las primitivas de seguridad: hash de contraseñas y tokens JWT."""

from datetime import datetime, timezone

import pytest
from jose import jwt

from app.config import JWT_ALGORITHM
from app.errors import AuthenticationError
from app.security import (
    PASSWORD_SCHEME,
    PBKDF2_ITERATIONS,
    ExpiredTokenError,
    InvalidTokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

SECRETO = "secreto-de-pruebas"
CONTRASENA = "clinic2024"


def test_el_hash_verifica_la_contrasena_correcta() -> None:
    hash_almacenado = hash_password(CONTRASENA)

    assert verify_password(CONTRASENA, hash_almacenado) is True


def test_el_hash_rechaza_una_contrasena_incorrecta() -> None:
    hash_almacenado = hash_password(CONTRASENA)

    assert verify_password("otra-clave", hash_almacenado) is False


def test_dos_hashes_de_la_misma_contrasena_son_distintos() -> None:
    primer_hash = hash_password(CONTRASENA)
    segundo_hash = hash_password(CONTRASENA)

    assert primer_hash != segundo_hash
    assert verify_password(CONTRASENA, primer_hash) is True
    assert verify_password(CONTRASENA, segundo_hash) is True


def test_el_hash_registra_el_esquema_las_iteraciones_y_la_sal() -> None:
    hash_almacenado = hash_password(CONTRASENA)

    esquema, iteraciones, sal_hex, hash_hex = hash_almacenado.split("$")

    assert esquema == PASSWORD_SCHEME
    assert int(iteraciones) == PBKDF2_ITERATIONS
    assert len(sal_hex) == 32
    assert len(hash_hex) == 64


@pytest.mark.parametrize(
    "hash_inesperado",
    [
        "",
        "basura",
        "pbkdf2_sha256$200000",
        "pbkdf2_sha256$200000$sal$hash",
        "bcrypt$200000$00112233$aabbccdd",
        "pbkdf2_sha256$no-numero$00112233$aabbccdd",
        "pbkdf2_sha256$200000$no-hex$aabbccdd",
        "pbkdf2_sha256$200000$00112233$no-hex",
    ],
)
def test_un_hash_inesperado_no_verifica_la_contrasena(hash_inesperado: str) -> None:
    assert verify_password(CONTRASENA, hash_inesperado) is False


def test_el_token_se_decodifica_con_su_carga_util() -> None:
    token = create_access_token(7, "client", secret=SECRETO)

    carga_util = decode_access_token(token, secret=SECRETO)

    assert carga_util["sub"] == "7"
    assert carga_util["role"] == "client"
    assert carga_util["exp"] == carga_util["iat"] + 3600
    assert carga_util["iat"] == pytest.approx(
        int(datetime.now(timezone.utc).timestamp()), abs=5
    )


def test_el_token_es_un_jwt_firmado_con_hs256() -> None:
    token = create_access_token(7, "vet", secret=SECRETO)

    assert len(token.split(".")) == 3
    assert jwt.get_unverified_header(token)["alg"] == JWT_ALGORITHM


def test_un_token_caducado_se_reporta_como_expirado() -> None:
    token = create_access_token(
        7, "client", secret=SECRETO, expires_in_seconds=-3600
    )

    with pytest.raises(ExpiredTokenError) as error:
        decode_access_token(token, secret=SECRETO)

    assert error.value.status_code == 401
    assert isinstance(error.value, AuthenticationError)


def test_un_token_firmado_con_otra_clave_es_invalido() -> None:
    token = create_access_token(7, "client", secret=SECRETO)

    with pytest.raises(InvalidTokenError) as error:
        decode_access_token(token, secret="otra-clave")

    assert error.value.status_code == 401


def test_un_token_mal_formado_es_invalido() -> None:
    with pytest.raises(InvalidTokenError) as error:
        decode_access_token("not-a-jwt", secret=SECRETO)

    assert error.value.status_code == 401
