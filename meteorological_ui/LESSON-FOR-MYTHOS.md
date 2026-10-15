# Lesson: how Mythos failed the "simple UI" task — and the fix

## What went wrong
1. User asked for a meteorological charts UI using DOC Weather data.
2. Mythos pasted a Flask tutorial with a **fake** `https://api.docweatherai.com` endpoint.
3. **No files were written.** Nothing was running.
4. User saw a blank/white screen and Mythos asked for more details instead of investigating.

## Efficient method (do this next time)
1. `list_dir` / `retrieve` — see if DOC / NWS code already exists.
2. Create a real folder under the workspace (`meteorological_ui/`).
3. `write_file` the server + HTML/CSS/JS.
4. `run_shell` to start the server.
5. Hit `/api/health` and open the UI URL. Fix until it renders.
6. Log one improvement.

## Shipped fix
- App: `~/coding-agent/meteorological_ui/`
- Run: `python3 server.py --port 8765`
- URL: http://127.0.0.1:8765/
- Data: free NWS + NOAA/SPC maps (no charges)
