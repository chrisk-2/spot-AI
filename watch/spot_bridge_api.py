from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

from spot_mcp_client import SpotClient


app = FastAPI(
    title="Spot Bridge API",
    version="0.1.0",
    description="ChatGPT Action bridge for Spot control-surface operations.",
)

TOOLS = [
    {"name": "spot_health", "method": "POST", "path": "/spot/health"},
    {"name": "spot_routing_audit", "method": "POST", "path": "/spot/routing-audit"},
    {"name": "spot_validate", "method": "POST", "path": "/spot/validate"},
    {"name": "spot_read_file", "method": "POST", "path": "/spot/read-file"},
    {"name": "spot_read_local_file", "method": "POST", "path": "/spot/read-local-file"},
    {"name": "spot_write_local_file", "method": "POST", "path": "/spot/write-local-file"},
    {"name": "spot_restart_service", "method": "POST", "path": "/spot/restart-service"},
    {"name": "spot_write_ui_file", "method": "POST", "path": "/spot/write-ui-file"},
]


def get_client() -> SpotClient:
    return SpotClient(
        base_url=os.environ.get("SPOT_BASE_URL", "http://127.0.0.1:8787").rstrip("/"),
        admin_token=os.environ.get("SPOT_ADMIN_TOKEN", "").strip(),
    )


class ValidateRequest(BaseModel):
    worker: str
    commands: list[str]


class ReadFileRequest(BaseModel):
    worker: str
    path: str


class ReadLocalFileRequest(BaseModel):
    path: str


class WriteLocalFileRequest(BaseModel):
    path: str
    content: str



class WriteUiFileRequest(BaseModel):
    filename: str
    content: str

class RestartServiceRequest(BaseModel):
    worker: str
    service: str


@app.get("/")
def root() -> dict[str, Any]:
    return {"name": "Spot Bridge API", "ok": True}


@app.get("/healthz")
def healthz() -> str:
    return "ok"


@app.get("/tools")
def tools() -> dict[str, Any]:
    return {"count": len(TOOLS), "tools": TOOLS}


@app.post("/spot/health")
def spot_health() -> dict[str, Any]:
    return get_client().health()


@app.post("/spot/routing-audit")
def spot_routing_audit(limit: int = 50) -> dict[str, Any]:
    return get_client().routing_audit(limit=limit)


@app.post("/spot/validate")
def spot_validate(req: ValidateRequest) -> dict[str, Any]:
    return get_client().validate(worker=req.worker, commands=req.commands)


@app.post("/spot/read-file")
def spot_read_file(req: ReadFileRequest) -> dict[str, Any]:
    return get_client().read_file(worker=req.worker, path=req.path)


@app.post("/spot/read-local-file")
def spot_read_local_file(req: ReadLocalFileRequest) -> dict[str, Any]:
    return get_client().read_local_file(path=req.path)


@app.post("/spot/write-local-file")
def spot_write_local_file(req: WriteLocalFileRequest) -> dict[str, Any]:
    return get_client().write_local_file(path=req.path, content=req.content)


@app.post("/spot/restart-service")
def spot_restart_service(req: RestartServiceRequest) -> dict[str, Any]:
    return get_client().restart_service(worker=req.worker, service=req.service)

@app.post("/spot/write-ui-file")
def spot_write_ui_file(req: WriteUiFileRequest) -> dict[str, Any]:
    return get_client().write_ui_file(filename=req.filename, content=req.content)
