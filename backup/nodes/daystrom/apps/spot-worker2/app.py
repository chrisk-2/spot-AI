from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

APP = FastAPI(title="spot-worker")
EXEC_TOKEN = os.environ.get("EXEC_TOKEN", "changeme")
JOBS_ROOT = Path(os.environ.get("JOBS_ROOT", "/mnt/collective/jobs"))
JOBS_OUT_ROOT = Path(os.environ.get("JOBS_OUT_ROOT", "/mnt/collective/jobs_out"))
NODE_NAME = os.environ.get("WORKER_NAME", socket.gethostname())
DEFAULT_TIMEOUT = int(os.environ.get("JOB_TIMEOUT_SEC", "900"))


class ExecBody(BaseModel):
    cmd: str
    args: dict[str, Any] = {}


def require_token(x_exec_token: str | None) -> None:
    if x_exec_token != EXEC_TOKEN:
        raise HTTPException(status_code=403, detail={"error": "bad_token"})


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return None


def _gpu_status() -> dict[str, Any]:
    cmd = [
        "nvidia-smi",
        "--query-gpu=index,name,pci.bus_id,memory.free,memory.total,utilization.gpu,utilization.memory,temperature.gpu,power.draw",
        "--format=csv,noheader,nounits",
    ]
    try:
        raw = subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT, timeout=10).strip()
    except Exception as exc:
        return {"ok": False, "error": "nvidia_smi_failed", "detail": str(exc)}

    gpus = []
    for line in raw.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 9:
            continue
        idx, name, bus, free_mb, total_mb, util_gpu, util_mem, temp_c, power_w = parts[:9]
        gpus.append(
            {
                "index": idx,
                "name": name,
                "pci_bus_id": bus,
                "vram_free_mb": int(float(free_mb)),
                "vram_total_mb": int(float(total_mb)),
                "util_gpu": f"{util_gpu} %",
                "util_mem": f"{util_mem} %",
                "temp_c": temp_c,
                "power_w": power_w,
            }
        )
    visible = os.environ.get("CUDA_VISIBLE_DEVICES")
    selected = gpus[0] if gpus else None
    if visible and gpus:
        try:
            idx = int(visible.split(",")[0])
            selected = next((g for g in gpus if int(g["index"]) == idx), selected)
        except Exception:
            pass
    return {"ok": True, "worker": NODE_NAME, "cuda_visible_devices": visible, "selected_gpu": selected, "gpus": gpus}


def _cuda_probe() -> str:
    py = shutil.which("python3") or "/usr/bin/python3"
    code = (
        "import os; "
        "print('PY=', os.getenv('VIRTUAL_ENV', 'system')); "
        "print('CUDA_VISIBLE_DEVICES=', os.getenv('CUDA_VISIBLE_DEVICES', '')); "
        "\ntry:\n import torch\n print('torch_version', torch.__version__)\n print('torch_cuda_available', torch.cuda.is_available())\n print('gpu_count', torch.cuda.device_count())\n print('gpu_name', torch.cuda.get_device_name(0) if torch.cuda.is_available() else '')\nexcept Exception as e:\n print('torch_error', e)"
    )
    out = subprocess.check_output([py, "-c", code], text=True, stderr=subprocess.STDOUT, timeout=20)
    return out


def _run_job(job: str, params: dict[str, Any], timeout_sec: int = DEFAULT_TIMEOUT) -> dict[str, Any]:
    script = JOBS_ROOT / f"{job}.sh"
    if not script.exists():
        return {"ok": False, "error": "job_not_found", "job": job, "script": str(script)}

    job_id = uuid.uuid4().hex[:12]
    out_dir = JOBS_OUT_ROOT / job / job_id
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "params.json").write_text(json.dumps(params or {}, indent=2), encoding="utf-8")

    env = os.environ.copy()
    env["JOB_ID"] = job_id
    env["JOB_NAME"] = job
    env["JOB_OUT_DIR"] = str(out_dir)
    env["OUT_DIR"] = str(out_dir)
    for key, value in (params or {}).items():
        env[str(key).upper()] = str(value)

    stdout_path = out_dir / "stdout.txt"
    stderr_path = out_dir / "stderr.txt"
    start = time.time()
    with stdout_path.open("w", encoding="utf-8") as out, stderr_path.open("w", encoding="utf-8") as err:
        proc = subprocess.run([
            "/usr/bin/env", "bash", str(script)
        ], cwd=str(JOBS_ROOT), env=env, stdout=out, stderr=err, timeout=timeout_sec, text=True)
    elapsed_ms = int((time.time() - start) * 1000)
    (out_dir / "rc.txt").write_text(str(proc.returncode), encoding="utf-8")
    return {
        "ok": proc.returncode == 0,
        "job": job,
        "job_id": job_id,
        "script": str(script),
        "out_dir": str(out_dir),
        "timeout_sec": timeout_sec,
        "rc": proc.returncode,
        "stdout": _read(stdout_path),
        "stderr": _read(stderr_path),
        "elapsed_ms": elapsed_ms,
    }


@APP.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True, "worker": NODE_NAME, "ts": int(time.time())}


@APP.post("/exec")
def exec_cmd(body: ExecBody, x_exec_token: str | None = Header(default=None)) -> dict[str, Any]:
    require_token(x_exec_token)
    cmd = body.cmd
    args = body.args or {}
    if cmd == "ping":
        return {"ok": True, "cmd": cmd, "returncode": 0, "stdout": "pong\n", "stderr": ""}
    if cmd == "gpu_status":
        return _gpu_status()
    if cmd == "cuda_probe":
        try:
            return {"ok": True, "stdout": _cuda_probe(), "stderr": ""}
        except Exception as exc:
            return {"ok": False, "error": "cuda_probe_failed", "stderr": str(exc)}
    if cmd == "vram_mb":
        status = _gpu_status()
        selected = status.get("selected_gpu") or {}
        return {"ok": status.get("ok", False), "stdout": f"{selected.get('vram_free_mb', 0)}\n"}
    if cmd == "run_job":
        return _run_job(args.get("job", ""), args.get("params", {}), int(args.get("timeout_sec", DEFAULT_TIMEOUT)))
    return {"ok": False, "error": "cmd_not_allowed", "cmd": cmd}
