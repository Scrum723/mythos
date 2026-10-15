# Meteorological UI (Doc Weather)

Simple local UI for forecast charts + upper-air / radar maps.

**NO CHARGES.** Uses free public data only:
- NWS API (`api.weather.gov`) for point forecast + hourly + alerts
- SPC / WPC / NWS radar public GIFs for upper air and radar

## Run

```bash
cd ~/coding-agent/meteorological_ui
python3 server.py --port 8765
```

Open http://127.0.0.1:8765/

## Why this exists

Mythos previously pasted a Flask tutorial with a fake `api.docweatherai.com` and never wrote files — so the browser stayed blank. This folder is the real shipped UI.
