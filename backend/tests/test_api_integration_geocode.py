from __future__ import annotations

from unittest.mock import patch

import httpx

from api_integration_base import ApiIntegrationTestCase
from transit_backend.api import server


class ApiGeocodeIntegrationTest(ApiIntegrationTestCase):
    def test_geocode_requires_city(self) -> None:
        response = self.client.get("/geocode", params={"q": "paris"})
        self.assertEqual(response.status_code, 400)

    def test_geocode_returns_empty_for_short_query(self) -> None:
        response = self.client.get("/geocode", params={"city": "paris_fr", "q": "ab"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"results": []})
        self.assertEqual(self.load_calls, [])

    def test_geocode_normalizes_provider_results(self) -> None:
        call_log: list[tuple[str, dict[str, object], dict[str, str]]] = []

        class FakeResponse:
            def raise_for_status(self) -> None:
                return None

            def json(self) -> object:
                return [
                    {
                        "display_name": "1 Avenue des Champs-Elysees, Paris",
                        "lat": "48.86982",
                        "lon": "2.30780",
                        "place_id": "123",
                        "osm_type": "way",
                        "osm_id": "456",
                        "address": {
                            "house_number": "1",
                            "road": "Avenue des Champs-Elysees",
                            "city": "Paris",
                            "country": "France",
                        },
                    },
                    {
                        "display_name": "205, Rue du Faubourg Saint-Martin, Quartier Saint-Vincent-de-Paul, Paris, France",
                        "lat": "48.88015",
                        "lon": "2.36380",
                        "place_id": "124",
                        "address": {
                            "house_number": "205",
                            "city": "Paris",
                            "country": "France",
                        },
                    },
                    {"display_name": "", "lat": "48.8", "lon": "2.3"},
                    {"display_name": "invalid", "lat": "invalid", "lon": "2.3"},
                ]

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
            response = self.client.get("/geocode", params={"city": "paris_fr", "q": "champs-elysees"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(
            payload["results"],
            [
                {
                    "id": "123",
                    "label": "1 Avenue des Champs-Elysees, Paris",
                    "lat": 48.86982,
                    "lon": 2.3078,
                },
                {
                    "id": "124",
                    "label": "205 Rue du Faubourg Saint-Martin, Paris",
                    "lat": 48.88015,
                    "lon": 2.3638,
                },
            ],
        )
        self.assertEqual(len(call_log), 1)
        self.assertEqual(call_log[0][1]["q"], "champs-elysees")
        self.assertEqual(call_log[0][1]["addressdetails"], 1)
        self.assertEqual(call_log[0][1]["limit"], server.GEOCODE_MAX_RESULTS)
        self.assertEqual(call_log[0][1]["countrycodes"], "fr")
        self.assertEqual(call_log[0][1]["viewbox"], "1.4472,48.1201,3.5590,49.2415")
        self.assertEqual(call_log[0][1]["bounded"], "1")
        self.assertEqual(call_log[0][2]["User-Agent"], server.GEOCODE_USER_AGENT)
        self.assertEqual(self.load_calls, [])

    def test_geocode_returns_502_on_provider_error(self) -> None:
        class FailingAsyncClient:
            def __init__(self, *_args: object, **_kwargs: object) -> None:
                return

            async def __aenter__(self) -> "FailingAsyncClient":
                return self

            async def __aexit__(
                self,
                _exc_type: object,
                _exc: object,
                _tb: object,
            ) -> bool:
                return False

            async def get(self, _url: str, **_kwargs: object) -> object:
                raise httpx.ConnectError("provider down")

        with patch("transit_backend.api.geocoding.httpx.AsyncClient", FailingAsyncClient):
            response = self.client.get("/geocode", params={"city": "paris_fr", "q": "paris"})

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json(), {"error": "geocoding provider unavailable"})
        self.assertEqual(self.load_calls, [])
