import json
import unittest
from unittest import mock
from urllib.parse import urlparse

from meteorological_ui import server as meteo


class MeteoServerTests(unittest.TestCase):
    def test_presets_buffalo(self):
        lat, lon, label = meteo.geocode_name("buffalo")
        self.assertAlmostEqual(lat, 42.8864, places=3)
        self.assertAlmostEqual(lon, -78.8784, places=3)
        self.assertTrue(label)

    def test_fetch_bundle_uses_nws_shape(self):
        point = {
            "properties": {
                "forecast": "https://api.weather.gov/gridpoints/BUF/38,47/forecast",
                "forecastHourly": "https://api.weather.gov/gridpoints/BUF/38,47/forecast/hourly",
                "cwa": "BUF",
                "gridId": "BUF",
                "gridX": 38,
                "gridY": 47,
                "relativeLocation": {"properties": {"city": "Buffalo", "state": "NY"}},
            }
        }
        forecast = {
            "properties": {
                "periods": [
                    {
                        "name": "Today",
                        "temperature": 70,
                        "temperatureUnit": "F",
                        "windSpeed": "10 mph",
                        "windDirection": "W",
                        "shortForecast": "Mostly Sunny",
                        "detailedForecast": "Nice",
                        "isDaytime": True,
                        "startTime": "2026-09-22T08:00:00-04:00",
                    }
                ]
            }
        }
        hourly = {
            "properties": {
                "periods": [
                    {
                        "startTime": "2026-09-22T08:00:00-04:00",
                        "temperature": 68,
                        "temperatureUnit": "F",
                        "windSpeed": "8 mph",
                        "shortForecast": "Sunny",
                        "probabilityOfPrecipitation": {"value": 10},
                    }
                ]
            }
        }
        alerts = {"features": []}

        def fake_json(url: str):
            if "/points/" in url:
                return point
            if url.endswith("/forecast"):
                return forecast
            if url.endswith("/forecast/hourly"):
                return hourly
            if "/alerts/" in url:
                return alerts
            raise AssertionError(url)

        with mock.patch.object(meteo, "_http_json", side_effect=fake_json):
            bundle = meteo.fetch_bundle(42.8864, -78.8784)
        self.assertEqual(bundle["office"], "BUF")
        self.assertEqual(bundle["periods"][0]["temperature"], 70)
        self.assertFalse(bundle["bills"])
        self.assertIn("500mb", bundle["maps"])

    def test_static_index_exists(self):
        self.assertTrue((meteo.STATIC / "index.html").is_file())
        self.assertTrue((meteo.STATIC / "app.js").is_file())


if __name__ == "__main__":
    unittest.main()
