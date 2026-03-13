from __future__ import annotations

import unittest

from transit_shared.settings_coercion import (
    as_bool,
    as_float,
    as_float_tuple,
    as_int,
    as_str,
    get_required,
    get_section,
)
from transit_shared.settings_schema import SettingsError


class SettingsCoercionTest(unittest.TestCase):
    def test_get_section_and_required(self) -> None:
        data = {"runtime": {"max_time_s": 3600}}
        self.assertEqual(get_section(data, "runtime"), {"max_time_s": 3600})
        self.assertEqual(get_required(data["runtime"], "max_time_s"), 3600)

        with self.assertRaises(SettingsError):
            get_section(data, "missing")
        with self.assertRaises(SettingsError):
            get_required(data["runtime"], "missing")

    def test_as_bool(self) -> None:
        self.assertEqual(as_bool(True, "x"), True)
        self.assertEqual(as_bool(False, "x"), False)
        with self.assertRaises(SettingsError):
            as_bool(1, "x")

    def test_as_int(self) -> None:
        self.assertEqual(as_int(3, "x"), 3)
        self.assertEqual(as_int("7", "x"), 7)
        with self.assertRaises(SettingsError):
            as_int(True, "x")
        with self.assertRaises(SettingsError):
            as_int("nan", "x")

    def test_as_float(self) -> None:
        self.assertAlmostEqual(as_float(1.25, "x"), 1.25)
        self.assertAlmostEqual(as_float("3.5", "x"), 3.5)
        with self.assertRaises(SettingsError):
            as_float(False, "x")
        with self.assertRaises(SettingsError):
            as_float("nope", "x")

    def test_as_str(self) -> None:
        self.assertEqual(as_str(" value ", "x"), "value")
        with self.assertRaises(SettingsError):
            as_str("", "x")
        with self.assertRaises(SettingsError):
            as_str("   ", "x")
        with self.assertRaises(SettingsError):
            as_str(123, "x")

    def test_as_float_tuple(self) -> None:
        self.assertEqual(as_float_tuple([1, "2"], "arr", 2), (1.0, 2.0))
        with self.assertRaises(SettingsError):
            as_float_tuple(12, "arr", 2)
        with self.assertRaises(SettingsError):
            as_float_tuple([1], "arr", 2)
