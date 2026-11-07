from __future__ import annotations

import json
import os
import platform
import shutil
import socket
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import PACKAGE_ROOT, Settings, local_reachable
from .defense import scan_exterior_risks
from .network_policy import is_loopback_url


def snapshot_path() -> Path:
    path = PACKAGE_ROOT / "data" / "watchdog"
    path.mkdir(parents=True, exist_ok=True)
    return path / "snapshots.jsonl"


def _device_snapshot() -> dict[str, Any]:
    ram_gb = None
    try:
        import ctypes

        if os.name == "nt":
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
                ram_gb = round(stat.ullTotalPhys / (1024**3), 2)
    except Exception:
        ram_gb = None
    disk = shutil.disk_usage(str(PACKAGE_ROOT))
    return {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "system": platform.system(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python": platform.python_version(),
        "cpu_count": os.cpu_count(),
        "ram_gb": ram_gb,
        "disk_free_gb": round(disk.free / (1024**3), 2),
        "disk_total_gb": round(disk.total / (1024**3), 2),
        "mythos_root": str(PACKAGE_ROOT),
    }


def _network_snapshot(settings: Settings) -> dict[str, Any]:
    loopback = is_loopback_url(settings.api_base)
    llm_up = bool(loopback and local_reachable(settings.api_base))
    # Default route / outbound capability — conservative: try UDP connect to localhost DNS-like probe
    has_route = False
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(0.5)
        sock.connect(("127.0.0.1", 9))
        has_route = True
        sock.close()
    except OSError:
        has_route = False
    risks = scan_exterior_risks(api_base=settings.api_base, airgap=bool(getattr(settings, "airgap", False)))
    return {
        "api_base_loopback": loopback,
        "loopback_llm": llm_up,
        "local_route_ok": has_route,
        "airgap": bool(getattr(settings, "airgap", False)),
        "exterior_risks": risks,
        "hostname_ip": _local_ips(),
    }


def _local_ips() -> list[str]:
    ips: list[str] = []
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None):
            ip = info[4][0]
            if ip not in ips:
                ips.append(ip)
    except OSError:
        pass
    return ips


def _devices_snapshot() -> list[dict[str, Any]]:
    """Connected devices inventory — local, non-offensive.

    Windows: list logical drives + optional PnP summary via PowerShell if available.
    Other OS: mount points / block-ish paths best-effort.
    """
    devices: list[dict[str, Any]] = []
    if os.name == "nt":
        for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
            root = f"{letter}:\\"
            if os.path.exists(root):
                try:
                    usage = shutil.disk_usage(root)
                    devices.append(
                        {
                            "name": f"{letter}:",
                            "kind": "volume",
                            "free_gb": round(usage.free / (1024**3), 2),
                            "total_gb": round(usage.total / (1024**3), 2),
                        }
                    )
                except OSError:
                    devices.append({"name": f"{letter}:", "kind": "volume", "error": "unreadable"})
        # Best-effort USB/PnP names (no admin required for basic list)
        try:
            import subprocess

            ps = (
                "Get-PnpDevice -PresentOnly -Status OK | "
                "Where-Object { $_.Class -in @('USB','DiskDrive','Net','Camera','Bluetooth') } | "
                "Select-Object -First 40 FriendlyName,Class | ConvertTo-Json -Compress"
            )
            proc = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps],
                capture_output=True,
                text=True,
                timeout=8,
                check=False,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                raw = json.loads(proc.stdout)
                if isinstance(raw, dict):
                    raw = [raw]
                for row in raw or []:
                    devices.append(
                        {
                            "name": row.get("FriendlyName") or "device",
                            "kind": (row.get("Class") or "pnp").lower(),
                        }
                    )
        except Exception:
            pass
    else:
        for mount in ("/", "/mnt", "/media", "/Volumes"):
            p = Path(mount)
            if p.exists():
                devices.append({"name": mount, "kind": "mount"})
    return devices


def watch_once(*, settings: Settings | None = None, path: Path | None = None) -> dict[str, Any]:
    settings = settings or Settings.load()
    path = path or snapshot_path()
    snap = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "network": _network_snapshot(settings),
        "device": _device_snapshot(),
        "devices": _devices_snapshot(),
    }
    prev = _last_snapshot(path)
    if prev:
        snap["diff_from_previous"] = compare_snapshots(prev, snap)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(snap, ensure_ascii=False) + "\n")
    return snap


def _last_snapshot(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if not lines:
        return None
    try:
        return json.loads(lines[-1])
    except json.JSONDecodeError:
        return None


def compare_snapshots(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    changes: list[str] = []
    an, bn = a.get("network") or {}, b.get("network") or {}
    for key in ("loopback_llm", "api_base_loopback", "airgap", "local_route_ok"):
        if an.get(key) != bn.get(key):
            changes.append(f"network.{key}: {an.get(key)} → {bn.get(key)}")
    ad, bd = a.get("device") or {}, b.get("device") or {}
    for key in ("hostname", "disk_free_gb", "ram_gb", "cpu_count"):
        if ad.get(key) != bd.get(key):
            changes.append(f"device.{key}: {ad.get(key)} → {bd.get(key)}")
    a_devs = {(d.get("kind"), d.get("name")) for d in (a.get("devices") or []) if isinstance(d, dict)}
    b_devs = {(d.get("kind"), d.get("name")) for d in (b.get("devices") or []) if isinstance(d, dict)}
    added = b_devs - a_devs
    removed = a_devs - b_devs
    for item in sorted(added):
        changes.append(f"devices added: {item[0]}:{item[1]}")
    for item in sorted(removed):
        changes.append(f"devices removed: {item[0]}:{item[1]}")
    return {"changes": changes, "changed": bool(changes)}


def watch_status(*, path: Path | None = None) -> dict[str, Any]:
    path = path or snapshot_path()
    snaps = []
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines()[-20:]:
            if not line.strip():
                continue
            try:
                snaps.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    last = snaps[-1] if snaps else None
    return {
        "snapshots": len(snaps),
        "path": str(path),
        "last": last,
        "note": "Local watchdog — network/device/devices over time. No offensive scanning.",
    }
