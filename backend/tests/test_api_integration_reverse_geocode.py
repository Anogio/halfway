from __future__ import annotations

from unittest.mock import patch

from api_integration_base import ApiIntegrationTestCase
from transit_backend.api import server


class ApiReverseGeocodeIntegrationTest(ApiIntegrationTestCase):
    def test_reverse_geocode_requires_city(self) -> None:
        response = self.client.get("/reverse_geocode", params={"lat": 48.89231, "lon": 2.39127})
        self.assertEqual(response.status_code, 400)

    def test_reverse_geocode_normalizes_provider_result(self) -> None:
        call_log: list[tuple[str, dict[str, object], dict[str, str]]] = []

        class FakeResponse:
            def raise_for_status(self) -> None:
                return None

            def json(self) -> object:
                return {
                    "display_name": "2, Rue Petit, Quartier de la Villette, Paris, France",
                    "lat": "48.89231",
                    "lon": "2.39127",
                    "address": {
                        "house_number": "2",
                        "road": "Rue Petit",
                        "city": "Paris",
                        "country": "France",
                    },
                }

        class FakeAsyncClient:
            def __init__(self, *_args: object, **_kwargs: object) -> None:
                return

            async def __aenter__(self) -> "FakeAsyncClient":
                return self

            async def __aexit__(
                self,
                _exc_type: object,
                _exc: object,
                _tb: object,
            ) -> bool:
                return False

            async def get(
                self,
                url: str,
                *,
                params: dict[str, object],
                headers: dict[str, str],
            ) -> FakeResponse:
                call_log.append((url, dict(params), dict(headers)))
                return FakeResponse()

        with patch("transit_backend.api.geocoding.httpx.AsyncClient", FakeAsyncClient):
            response = self.client.get(
                "/reverse_geocode",
                params={"city": "paris_fr", "lat": 48.89231, "lon": 2.39127},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"label": "2 Rue Petit, Paris"})
        self.assertEqual(len(call_log), 1)
        self.assertEqual(call_log[0][1]["lat"], 48.89231)
        self.assertEqual(call_log[0][1]["lon"], 2.39127)
        self.assertEqual(call_log[0][1]["addressdetails"], 1)
        self.assertEqual(call_log[0][2]["User-Agent"], server.GEOCODE_USER_AGENT)

    def test_reverse_geocode_returns_404_when_provider_has_no_result(self) -> None:
        class EmptyResponse:
            def raise_for_status(self) -> None:
                return None

            def json(self) -> object:
                return {"error": "Unable to geocode"}

        class FakeAsyncClient:
            def __init__(self, *_args: object, **_kwargs: object) -> None:
                return

            async def __aenter__(self) -> "FakeAsyncClient":
                return self

            async def __aexit__(
                self,
                _exc_type: object,
                _exc: object,
                _tb: object,
            ) -> bool:
                return False

            async def get(self, _url: str, **_kwargs: object) -> EmptyResponse:
                return EmptyResponse()

        with patch("transit_backend.api.geocoding.httpx.AsyncClient", FakeAsyncClient):
            response = self.client.get(
                "/reverse_geocode",
                params={"city": "paris_fr", "lat": 48.85, "lon": 2.35},
            )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"error": "not found"})
