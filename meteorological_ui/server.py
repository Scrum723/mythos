#!/usr/bin/env python3
"""Simple meteorological charts UI — free NWS + public NOAA/SPC maps. NO CHARGES."""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
STATIC = HERE / "static"
NWS = "https://api.weather.gov"
UA = "DocWeatherMythosUI/1.0 (local; charlesclottin; contact: local-dev)"

# Common places for quick picks (lat, lon)
PRESETS = {
    "buffalo": (42.8864, -78.8784),
    "rochester": (43.1566, -77.6088),
    "syracuse": (43.0481, -76.1474),
    "nyc": (40.7128, -74.0060),
    "chicago": (41.8781, -87.6298),
    "denver": (39.7392, -104.9903),
}

UPPER_AIR = {
    "surface": {
        "label": "WPC Surface Analysis",
        "url": "https://www.wpc.ncep.noaa.gov/noaa/noaad1.gif",
    },
    "500mb": {
        "label": "SPC 500 mb",
        "url": "https://www.spc.noaa.gov/obswx/maps/500mb.gif",
    },
    "850mb": {
        "label": "SPC 850 mb",
        "url": "https://www.spc.noaa.gov/obswx/maps/850mb.gif",
    },
    "300mb": {
        "label": "SPC 300 mb",
        "url": "https://www.spc.noaa.gov/obswx/maps/300mb.gif",
    },
    "radar_kbuf": {
        "label": "KBUF Radar Loop",
        "url": "https://radar.weather.gov/ridge/standard/KBUF_loop.gif",
    },
}


def _http_json(url: str) -> dict:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": UA, "Accept": "application/geo+json, application/json"},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def geocode_name(name: str) -> tuple[float, float, str]:
    key = name.strip().lower().replace(" ", "")
    if key in PRESETS:
        lat, lon = PRESETS[key]
        return lat, lon, name.strip().title()
    # Free Nominatim (OpenStreetMap) — no API key
    q = urllib.parse.quote(name.strip())
    url = f"https://nominatim.openstreetmap.org/search?q={q}&format=json&limit=1"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as resp:
        rows = json.loads(resp.read().decode("utf-8"))
    if not rows:
        raise ValueError(f"location not found: {name!r}")
    row = rows[0]
    return float(row["lat"]), float(row["lon"]), row.get("display_name") or name


def fetch_bundle(lat: float, lon: float) -> dict:
    point = _http_json(f"{NWS}/points/{lat:.4f},{lon:.4f}")
    props = point.get("properties") or {}
    forecast_url = props.get("forecast")
    hourly_url = props.get("forecastHourly")
    office = props.get("cwa") or ""
    grid = f"{props.get('gridId')} {props.get('gridX')},{props.get('gridY')}"
    city = ((props.get("relativeLocation") or {}).get("properties") or {}).get("city") or ""
    state = ((props.get("relativeLocation") or {}).get("properties") or {}).get("state") or ""

    periods = []
    hourly = []
    if forecast_url:
        forecast = _http_json(forecast_url)
        periods = (forecast.get("properties") or {}).get("periods") or []
    if hourly_url:
        hourly_data = _http_json(hourly_url)
        hourly = ((hourly_data.get("properties") or {}).get("periods") or [])[:48]

    alerts = []
    try:
        alert_json = _http_json(f"{NWS}/alerts/active?point={lat:.4f},{lon:.4f}")
        for feat in alert_json.get("features") or []:
            p = feat.get("properties") or {}
            alerts.append(
                {
                    "event": p.get("event"),
                    "headline": p.get("headline"),
                    "severity": p.get("severity"),
                    "expires": p.get("expires"),
                }
            )
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
        pass

    return {
        "lat": lat,
        "lon": lon,
        "place": f"{city}, {state}".strip(", "),
        "office": office,
        "grid": grid,
        "periods": [
            {
                "name": p.get("name"),
                "startTime": p.get("startTime"),
                "temperature": p.get("temperature"),
                "temperatureUnit": p.get("temperatureUnit"),
                "windSpeed": p.get("windSpeed"),
                "windDirection": p.get("windDirection"),
                "shortForecast": p.get("shortForecast"),
                "detailedForecast": p.get("detailedForecast"),
                "isDaytime": p.get("isDaytime"),
            }
            for p in periods
        ],
        "hourly": [
            {
                "startTime": h.get("startTime"),
                "temperature": h.get("temperature"),
                "temperatureUnit": h.get("temperatureUnit"),
                "windSpeed": h.get("windSpeed"),
                "shortForecast": h.get("shortForecast"),
                "probabilityOfPrecipitation": (h.get("probabilityOfPrecipitation") or {}).get("value"),
            }
            for h in hourly
        ],
        "alerts": alerts,
        "maps": UPPER_AIR,
        "source": "api.weather.gov + public NOAA/SPC map GIFs (free)",
        "bills": False,
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        print(f"[meteo] {self.address_string()} {fmt % args}")

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, payload: dict) -> None:
        raw = json.dumps(payload, indent=2).encode("utf-8")
        self._send(code, raw, "application/json; charset=utf-8")

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        qs = urllib.parse.parse_qs(parsed.query)

        if path in {"/", "/index.html"}:
            html = (STATIC / "index.html").read_bytes()
            self._send(200, html, "text/html; charset=utf-8")
            return
        if path.startswith("/static/"):
            rel = path[len("/static/") :]
            target = (STATIC / rel).resolve()
            if not str(target).startswith(str(STATIC.resolve())) or not target.is_file():
                self._json(404, {"error": "not found"})
                return
            ctype = {
                ".js": "application/javascript; charset=utf-8",
                ".css": "text/css; charset=utf-8",
                ".html": "text/html; charset=utf-8",
                ".svg": "image/svg+xml",
            }.get(target.suffix.lower(), "application/octet-stream")
            self._send(200, target.read_bytes(), ctype)
            return
        if path == "/api/health":
            self._json(
                200,
                {
                    "service": "meteorological_ui",
                    "ok": True,
                    "bills": False,
                    "data": "NWS + NOAA/SPC public maps",
                },
            )
            return
        if path == "/api/presets":
            self._json(200, {"presets": sorted(PRESETS)})
            return
        if path == "/api/maps":
            self._json(200, {"maps": UPPER_AIR})
            return
        if path == "/api/forecast":
            try:
                if "lat" in qs and "lon" in qs:
                    lat = float(qs["lat"][0])
                    lon = float(qs["lon"][0])
                    label = qs.get("name", [f"{lat},{lon}"])[0]
                elif "q" in qs and qs["q"][0].strip():
                    lat, lon, label = geocode_name(qs["q"][0])
                else:
                    lat, lon = PRESETS["buffalo"]
                    label = "Buffalo"
                bundle = fetch_bundle(lat, lon)
                if not bundle.get("place"):
                    bundle["place"] = label
                self._json(200, bundle)
            except Exception as exc:  # noqa: BLE001 — surface to UI
                self._json(400, {"error": str(exc)})
            return

        self._json(404, {"error": "not found"})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Meteorological charts UI (free NWS data)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Meteorological UI → http://{args.host}:{args.port}/")
    print("Data: api.weather.gov + NOAA/SPC public maps. NO CHARGES.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
