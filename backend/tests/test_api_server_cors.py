from __future__ import annotations

import os
import unittest

from transit_backend.api.server import require_cors_settings


class ApiServerCorsTest(unittest.TestCase):
    def test_require_cors_settings_returns_explicit_origin(self) -> None:
        previous_origin = os.environ.get("CORS_ALLOW_ORIGIN")
        previous_origin_regex = os.environ.get("CORS_ALLOW_ORIGIN_REGEX")
        try:
            os.environ["CORS_ALLOW_ORIGIN"] = "https://www.halfway.anog.fr"
            os.environ.pop("CORS_ALLOW_ORIGIN_REGEX", None)
            self.assertEqual(require_cors_settings(), (["https://www.halfway.anog.fr"], None))
        finally:
            if previous_origin is None:
                os.environ.pop("CORS_ALLOW_ORIGIN", None)
            else:
                os.environ["CORS_ALLOW_ORIGIN"] = previous_origin
            if previous_origin_regex is None:
                os.environ.pop("CORS_ALLOW_ORIGIN_REGEX", None)
            else:
                os.environ["CORS_ALLOW_ORIGIN_REGEX"] = previous_origin_regex

    def test_require_cors_settings_accepts_regex_only(self) -> None:
        previous_origin = os.environ.get("CORS_ALLOW_ORIGIN")
        previous_origin_regex = os.environ.get("CORS_ALLOW_ORIGIN_REGEX")
        try:
            os.environ.pop("CORS_ALLOW_ORIGIN", None)
            os.environ["CORS_ALLOW_ORIGIN_REGEX"] = r"^http://(localhost|127\.0\.0\.1):3[0-9]{3}$"
            self.assertEqual(
                require_cors_settings(),
                ([], r"^http://(localhost|127\.0\.0\.1):3[0-9]{3}$"),
            )
        finally:
            if previous_origin is None:
                os.environ.pop("CORS_ALLOW_ORIGIN", None)
            else:
                os.environ["CORS_ALLOW_ORIGIN"] = previous_origin
            if previous_origin_regex is None:
                os.environ.pop("CORS_ALLOW_ORIGIN_REGEX", None)
            else:
                os.environ["CORS_ALLOW_ORIGIN_REGEX"] = previous_origin_regex

    def test_require_cors_settings_rejects_missing_values(self) -> None:
        previous_origin = os.environ.get("CORS_ALLOW_ORIGIN")
        previous_origin_regex = os.environ.get("CORS_ALLOW_ORIGIN_REGEX")
        try:
            os.environ.pop("CORS_ALLOW_ORIGIN", None)
            os.environ.pop("CORS_ALLOW_ORIGIN_REGEX", None)
            with self.assertRaisesRegex(RuntimeError, "CORS_ALLOW_ORIGIN or CORS_ALLOW_ORIGIN_REGEX must be set"):
                require_cors_settings()
        finally:
            if previous_origin is None:
                os.environ.pop("CORS_ALLOW_ORIGIN", None)
            else:
                os.environ["CORS_ALLOW_ORIGIN"] = previous_origin
            if previous_origin_regex is None:
                os.environ.pop("CORS_ALLOW_ORIGIN_REGEX", None)
            else:
                os.environ["CORS_ALLOW_ORIGIN_REGEX"] = previous_origin_regex
