from __future__ import annotations

import os
from typing import Any

import requests


SPOT_BASE_URL = os.environ.get("SPOT_BASE_URL", "http://127.0.0.1:8787").rstrip("/")
SPOT_ADMIN_TOKEN = os.environ.get("SPOT_ADMIN_TOKEN", "")


class SpotClient:
    def read_local_file(self, path: str) -> dict[str, Any]:
        return self._post("/admin/read-local-file", {"path": path}, admin=True)

    def write_local_file(self, path: str, content: str) -> dict[str, Any]:
        return self._post("/admin/write-local-file", {"path": path, "content": content}, admin=True)

    def __init__(self, base_url: str = SPOT_BASE_URL, admin_token: str = SPOT_ADMIN_TOKEN) -> None:
        self.base_url = base_url.rstrip("/")
        self.admin_token = admin_token

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        resp = requests.get(f"{self.base_url}{path}", params=params, timeout=60)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, payload: dict[str, Any], admin: bool = False) -> dict[str, Any]:
        body = dict(payload)
        if admin:
            if not self.admin_token:
                raise RuntimeError("SPOT_ADMIN_TOKEN is not set")
            body["token"] = self.admin_token
        resp = requests.post(f"{self.base_url}{path}", json=body, timeout=300)
        resp.raise_for_status()
        return resp.json()

    def health(self) -> dict[str, Any]:
        return self._get("/health")

    def routing(self) -> dict[str, Any]:
        return self._get("/routing")

    def fleet_ping(self) -> dict[str, Any]:
        return self._get("/fleet/ping")

    def stats_latency(self) -> dict[str, Any]:
        return self._get("/stats/latency")

    def recent_decisions(self, limit: int = 25) -> dict[str, Any]:
        return self._get("/stats/recent-decisions", params={"limit": limit})

    def routing_audit(self, limit: int = 200) -> dict[str, Any]:
        return self._get("/stats/routing-audit", params={"limit": limit})

    def read_file(self, worker: str, path: str) -> dict[str, Any]:
        return self._post("/admin/read-file", {"worker": worker, "path": path}, admin=True)

    def validate(self, worker: str, commands: list[str]) -> dict[str, Any]:
        return self._post("/admin/validate", {"worker": worker, "commands": commands}, admin=True)

    def write_file(self, worker: str, path: str, content: str) -> dict[str, Any]:
        return self._post(
            "/admin/write-file",
            {"worker": worker, "path": path, "content": content},
            admin=True,
        )

    def restart_service(self, worker: str, service: str) -> dict[str, Any]:
        return self._post(
            "/admin/restart-service",
            {"worker": worker, "service": service},
            admin=True,
        )

    def quarantine_worker(self, worker: str, seconds: int = 1800, reason: str = "manual_quarantine") -> dict[str, Any]:
        return self._post(
            "/admin/quarantine",
            {"worker": worker, "seconds": seconds, "reason": reason},
            admin=True,
        )

    def release_worker(self, worker: str) -> dict[str, Any]:
        return self._post("/admin/release", {"worker": worker}, admin=True)

    def exec(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._post("/exec", payload, admin=False)
