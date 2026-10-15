from __future__ import annotations

import json
import threading
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from . import coach, improve
from .agent import run_task
from .config import PACKAGE_ROOT, Settings
from .constitution import identity
from .languages import detect
from .spawn import list_agents, spawn
from .tools import ConfirmationRequired, ToolBox

WEB_DIR = PACKAGE_ROOT / "web"


class Desk:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.lock = threading.Lock()
        self.events: deque[dict[str, Any]] = deque(maxlen=400)
        self.seq = 0
        self.busy = False
        self.pending: dict[str, Any] | None = None
        self._confirm = threading.Event()
        self._confirm_ok = False
        self.last_report = ""

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            ident = identity()
            return {
                "service": ident.get("name") or "coding",
                "role": ident.get("role") or "",
                "root": str(self.settings.root),
                "autonomy": self.settings.autonomy,
                "provider": self.settings.provider,
                "model": self.settings.model,
                "has_llm": self.settings.has_llm,
                "bills_xai": self.settings.uses_xai,
                "busy": self.busy,
                "pending": self.pending,
                "seq": self.seq,
                "language": detect(self.settings.root),
                "last_report": self.last_report,
            }

    def emit(self, event: dict[str, Any]) -> None:
        with self.lock:
            self.seq += 1
            item = {"id": self.seq, **event}
            self.events.append(item)

    def events_since(self, since: int) -> list[dict[str, Any]]:
        with self.lock:
            return [e for e in self.events if e["id"] > since]

    def confirmer(self, tool: str, args: dict[str, Any], reason: str, risk: str) -> bool:
        with self.lock:
            self.pending = {"tool": tool, "args": args, "reason": reason, "risk": risk}
            self._confirm.clear()
            self._confirm_ok = False
        self.emit({"type": "confirm", "data": self.pending})
        ok = self._confirm.wait(timeout=600)
        with self.lock:
            approved = bool(ok and self._confirm_ok)
            self.pending = None
        return approved

    def resolve(self, approve: bool) -> bool:
        with self.lock:
            if not self.pending:
                return False
            self._confirm_ok = approve
            self._confirm.set()
        return True

    def start_run(self, task: str, autonomy: int | None) -> str:
        with self.lock:
            if self.busy:
                return "busy"
            self.busy = True
            self.last_report = ""
            if autonomy is not None:
                self.settings.autonomy = autonomy
        thread = threading.Thread(target=self._run, args=(task,), daemon=True)
        thread.start()
        return "started"

    def _run(self, task: str) -> None:
        self.emit({"type": "start", "data": {"task": task, "autonomy": self.settings.autonomy}})
        try:
            result = run_task(
                task,
                settings=self.settings,
                confirmer=self.confirmer,
                listener=lambda e: self.emit(e),
            )
            self.last_report = result.report
            self.emit({"type": "done", "data": {"ok": result.ok, "report": result.report}})
        except Exception as exc:  # noqa: BLE001 — desk must never die mid-run
            self.emit({"type": "error", "data": {"message": str(exc)}})
        finally:
            with self.lock:
                self.busy = False
                self.pending = None


def make_server(settings: Settings, host: str = "127.0.0.1", port: int = 8790) -> ThreadingHTTPServer:
    desk = Desk(settings)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: Any) -> None:
            sys_stderr = __import__("sys").stderr
            sys_stderr.write("[coding] " + (fmt % args) + "\n")

        def _json(self, code: int, payload: Any) -> None:
            raw = json.dumps(payload, default=str).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(raw)

        def _read_json(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length") or "0")
            if length > 1_000_000:
                raise ValueError("body too large")
            if length <= 0:
                return {}
            raw = self.rfile.read(length)
            data = json.loads(raw.decode("utf-8"))
            if not isinstance(data, dict):
                raise ValueError("JSON object required")
            return data

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = parsed.path
            if path in {"/", "/index.html"}:
                return self._static("index.html", "text/html; charset=utf-8")
            if path == "/styles.css":
                return self._static("styles.css", "text/css; charset=utf-8")
            if path == "/app.js":
                return self._static("app.js", "application/javascript; charset=utf-8")
            if path == "/api/health":
                return self._json(200, desk.snapshot())
            if path == "/api/events":
                qs = parse_qs(parsed.query)
                since = int((qs.get("since") or ["0"])[0])
                return self._json(200, {"events": desk.events_since(since), "seq": desk.seq, "busy": desk.busy})
            if path == "/api/agents":
                return self._json(200, {"agents": list_agents()})
            if path == "/api/improvements":
                return self._json(200, {"improvements": improve.read_all()})
            if path == "/api/language":
                return self._json(200, detect(desk.settings.root))
            return self._json(404, {"error": "not found"})

        def do_POST(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = parsed.path
            try:
                body = self._read_json()
            except (ValueError, json.JSONDecodeError) as exc:
                return self._json(400, {"error": str(exc)})
            if path == "/api/run":
                task = str(body.get("task") or "").strip()
                if not task:
                    return self._json(400, {"error": "task is required"})
                autonomy = body.get("autonomy")
                if autonomy is not None:
                    try:
                        autonomy = int(autonomy)
                    except (TypeError, ValueError):
                        return self._json(400, {"error": "autonomy must be 1-5"})
                    if autonomy < 1 or autonomy > 5:
                        return self._json(400, {"error": "autonomy must be 1-5"})
                status = desk.start_run(task, autonomy)
                code = 409 if status == "busy" else 202
                return self._json(code, {"status": status})
            if path == "/api/confirm":
                ok = desk.resolve(bool(body.get("approve")))
                return self._json(200 if ok else 409, {"ok": ok})
            if path == "/api/spawn":
                try:
                    result = spawn(
                        name=str(body.get("name") or ""),
                        role=str(body.get("role") or ""),
                        prompt=str(body.get("prompt") or ""),
                        tools=str(body.get("tools") or "list_dir,read_file,write_file,grep,run_shell,run_tests"),
                        constraints=str(body.get("constraints") or "Stay in project root. No secrets. Honesty first."),
                    )
                except ValueError as exc:
                    return self._json(400, {"error": str(exc)})
                return self._json(201, result)
            if path == "/api/autonomy":
                try:
                    level = int(body.get("level"))
                except (TypeError, ValueError):
                    return self._json(400, {"error": "level must be 1-5"})
                if level < 1 or level > 5:
                    return self._json(400, {"error": "level must be 1-5"})
                desk.settings.autonomy = level
                return self._json(200, {"autonomy": level})
            if path == "/api/improve":
                raw_path = str(body.get("path") or body.get("target") or "").strip()
                apply = bool(body.get("apply"))
                try:
                    target = coach.resolve_target(raw_path)
                except coach.TargetError as exc:
                    return self._json(400, {"error": str(exc)})
                report = coach.scan(target)
                if apply:
                    if desk.busy:
                        return self._json(409, {"error": "busy", "scan": report})
                    if not desk.settings.has_llm:
                        return self._json(
                            409,
                            {
                                "error": "Local Ollama is not available. Scan only — will not call a paid API or pretend to patch.",
                                "scan": report,
                            },
                        )
                    desk.settings.root = target
                    desk.start_run(coach.improve_task(target, apply=True), desk.settings.autonomy)
                    return self._json(202, {"status": "started", "scan": report})
                return self._json(200, report)
            if path == "/api/tool":
                name = str(body.get("name") or "")
                args = body.get("args") or {}
                if not isinstance(args, dict):
                    return self._json(400, {"error": "args must be an object"})
                box = ToolBox(desk.settings, confirmer=desk.confirmer)
                try:
                    output = box.execute(name, args)
                except ConfirmationRequired as pending:
                    return self._json(
                        409,
                        {
                            "error": "confirmation required",
                            "reason": pending.reason,
                            "risk": pending.risk,
                        },
                    )
                return self._json(200, {"output": output})
            return self._json(404, {"error": "not found"})

        def _static(self, name: str, content_type: str) -> None:
            path = (WEB_DIR / name).resolve()
            try:
                path.relative_to(WEB_DIR.resolve())
            except ValueError:
                return self._json(403, {"error": "forbidden"})
            if not path.is_file():
                return self._json(404, {"error": "missing ui file"})
            data = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    httpd = ThreadingHTTPServer((host, port), Handler)
    httpd.desk = desk  # type: ignore[attr-defined]
    return httpd


def serve(settings: Settings, host: str = "127.0.0.1", port: int = 8790) -> None:
    httpd = make_server(settings, host, port)
    ident = identity()
    label = ident.get("name") or "coding"
    print(f"{label} desk  http://{host}:{port}  autonomy={settings.autonomy}  root={settings.root}")
    if host in {"0.0.0.0", "::", "[::]"}:
        print("WARNING: listening on all interfaces with no auth. Do not publish this port.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopping")
        httpd.server_close()
