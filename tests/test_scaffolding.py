"""Comprobaciones del esqueleto de paquetes del proyecto."""

import importlib

import pytest


@pytest.mark.parametrize("nombre_modulo", ["app", "app.routers", "app.services"])
def test_los_paquetes_del_proyecto_son_importables(nombre_modulo: str) -> None:
    assert importlib.import_module(nombre_modulo) is not None
