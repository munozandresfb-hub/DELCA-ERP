"""Tests del parser de dimensiones (v2.6.0)."""

import pytest

from scripts.importar_llantas_csv import parsear_dimension


class TestParsearDimension:
    """parsear_dimension() — formatos del sistema legacy."""

    def test_metrico_estandar(self):
        # 295/80R22.5 -> (295, 80, 22.5, '')
        assert parsear_dimension("295/80R22.5") == (295.0, 80, 22.5, "")

    def test_metrico_ancho_decimal(self):
        # v2.6.0: ancho decimal
        assert parsear_dimension("9.5R17.5") == (9.5, None, 17.5, "")
        assert parsear_dimension("7.50R16") == (7.5, None, 16.0, "")

    def test_metrico_con_sufijo(self):
        # v2.6.0: sufijo visible
        assert parsear_dimension("215/75R16C") == (215.0, 75, 16.0, "C")
        assert parsear_dimension("295/80R22.5U") == (295.0, 80, 22.5, "U")

    def test_metrico_con_guion(self):
        # 215/75-15 (guion en vez de R)
        assert parsear_dimension("215/75-15") == (215.0, 75, 15.0, "")

    def test_convencional_rin_decimal(self):
        # v2.6.0: rin decimal en convencional
        assert parsear_dimension("12-22.5") == (12.0, None, 22.5, "")
        assert parsear_dimension("12-16.5") == (12.0, None, 16.5, "")

    def test_convencional_con_sufijo(self):
        assert parsear_dimension("7.50-16U") == (7.5, None, 16.0, "U")

    def test_flotacion(self):
        # 31X10.50R15 -> ancho de banda 10.5, rin 15
        assert parsear_dimension("31X10.50R15") == (10.5, None, 15.0, "")

    def test_especial_sin_ancho(self):
        # H78-15 -> ancho None, rin 15
        assert parsear_dimension("H78-15") == (None, None, 15.0, "")

    def test_minusculas(self):
        assert parsear_dimension("295/80r22.5") == (295.0, 80, 22.5, "")

    def test_no_parseable(self):
        assert parsear_dimension("") is None
        assert parsear_dimension("ABC") is None
        assert parsear_dimension("x1y2z3") is None