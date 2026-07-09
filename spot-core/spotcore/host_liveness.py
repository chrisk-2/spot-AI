from __future__ import annotations

import datetime as _dt
import json
import re
import shutil
import socket
import subprocess
import time
from pathlib import Path
from typing import Any

DEFAULT_REGISTRY = Path(__file__).resolve().parents[1] / "config" / "host_registry.json"


def _utc_now() -> str:
    return _dt.datetime.now(_dt.UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_registry(path: str | Path | None = None) -> list[dict[str, Any]]:
    registry_path = Path(path) if path else DEFAULT_REGISTRY
    data = json.loads(registry_path.read_text(encoding="utf-8"))
    hosts = data.get("hosts", data if isinstance(data, list) else [])
    if not isinstance(hosts, list):
        raise ValueError(f"invalid host registry format: {registry_path}")
    return hosts


def _resolve_ip(address: str) -> str:
    try:
        return socket.gethostbyname(address)
    except Exception:
        return address


def _ping(address: str) -> tuple[bool, float | None]:
    ping = shutil.which("ping")
    if not ping:
        return False, None

    start = time.perf_counter()
    proc = subprocess.run(
        [ping, "-c", "1", "-W", "1", address],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        timeout=3,
        check=False,
    )
    elapsed = round((time.perf_counter() - start) * 1000, 2)

    if proc.returncode != 0:
        return False, None

    m = re.search(r"time[=<]([0-9.]+)\s*ms", proc.stdout)
    latency = round(float(m.group(1)), 2) if m else elapsed
    return True, latency


def _tcp_check(address: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((address, int(port)), timeout=timeout):
            return True
    except Exception:
        return False


def admin_host_liveness(targets: str | list[str] | None = "all", registry_path: str | Path | None = None) -> list[dict[str, Any]]:
    hosts = _load_registry(registry_path)

    if targets is None or targets == "all" or targets == ["all"]:
        selected = hosts
    else:
        wanted = {targets} if isinstance(targets, str) else set(targets)
        by_name = {h.get("name"): h for h in hosts}
        missing = sorted(wanted - set(by_name))
        if missing:
            raise ValueError(f"unknown host target(s): {', '.join(missing)}")
        selected = [by_name[name] for name in sorted(wanted)]

    checked_at = _utc_now()
    results: list[dict[str, Any]] = []

    for host in selected:
        name = str(host.get("name", "unknown"))
        raw_ip = str(host.get("ip") or host.get("address") or name)
        ip = _resolve_ip(raw_ip)
        method = str(host.get("probe_method", "icmp")).lower()
        ports = [int(p) for p in host.get("expected_ports", [])]

        icmp_ok = False
        latency_ms = None
        if method in {"icmp", "both"}:
            icmp_ok, latency_ms = _ping(ip)

        port_checks = []
        any_port_open = False
        if method in {"tcp", "both"}:
            for port in ports:
                open_ = _tcp_check(ip, port)
                any_port_open = any_port_open or open_
                port_checks.append({"port": port, "open": open_})

        reachable = icmp_ok if method == "icmp" else any_port_open if method == "tcp" else (icmp_ok or any_port_open)

        if icmp_ok:
            used_method = "icmp"
        elif any_port_open:
            used_method = "tcp"
        else:
            used_method = method

        results.append(
            {
                "name": name,
                "ip": ip,
                "reachable": bool(reachable),
                "method": used_method,
                "latency_ms": latency_ms,
                "checked_at": checked_at,
                "port_checks": port_checks,
            }
        )

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Read-only host liveness probe from Spot Core.")
    parser.add_argument("targets", nargs="*", default=["all"])
    args = parser.parse_args()
    targets: str | list[str] = "all" if args.targets == ["all"] else args.targets
    print(json.dumps(admin_host_liveness(targets), indent=2))
