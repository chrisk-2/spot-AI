from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import requests
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

SPOT_GATEWAY = "http://192.168.10.10:8798"
JOBS_DIR = "/mnt/collective/jobs_out/llm_infer_stream"

APP = FastAPI(title="readyroom-ui")
BASE_DIR = Path(__file__).resolve().parent
TEMPLATES = Jinja2Templates(directory=str(BASE_DIR / "templates"))
APP.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

SPOT_BRAIN_URL = os.environ.get("SPOT_BRAIN_URL", "http://192.168.10.10:8798")
JOBS_OUT_ROOT = Path(os.environ.get("JOBS_OUT_ROOT", "/mnt/collective/jobs_out"))

DEFAULT_MODEL = os.environ.get("READYROOM_DEFAULT_MODEL", "qwen2.5:14b")
FAST_MODEL = os.environ.get("READYROOM_FAST_MODEL", "llama3.1:8b")
BUILD_MODEL = os.environ.get("READYROOM_BUILD_MODEL", "qwen2.5:14b")
CODE_MODEL = os.environ.get("READYROOM_CODE_MODEL", "deepseek-coder:6.7b")

EXTRA_MODELS = [
    m.strip()
    for m in os.environ.get(
        "READYROOM_EXTRA_MODELS",
        "mistral:7b,codellama:7b,qwen2.5-coder:7b,nomic-embed-text:latest,bge-m3:latest,phi3.5:latest,gemma3:4b"
    ).split(",")
    if m.strip()
]

ALLOWED_MODELS = []
for m in [FAST_MODEL, BUILD_MODEL, CODE_MODEL, *EXTRA_MODELS]:
    if m and m not in ALLOWED_MODELS:
        ALLOWED_MODELS.append(m)

REPO_JOB_NAME = os.environ.get("READYROOM_REPO_JOB_NAME", "starfleet_repo")

def pick_worker_for_model(model: str) -> str | None:
    model = (model or "").strip()
    return None

class PromptBody(BaseModel):
    prompt: str
    model: str | None = "auto"
    system: str | None = None
    preferred_worker: str | None = None

class JobBody(BaseModel):
    job: str
    params: dict[str, Any] = {}
    job_class: str | None = None


class RepoActionBody(BaseModel):
    cmd: str
    file: str = ""
    text: str = ""


class GenerateRepoDraftBody(BaseModel):
    prompt: str
    file: str = ""
    model: str = DEFAULT_MODEL

@APP.get("/api/fleet_summary")
def fleet_summary():
    try:
        gpu = requests.get(f"{SPOT_GATEWAY}/cluster/gpu_status", timeout=5).json()
    except Exception:
        return {"ok": False, "error": "gateway_unreachable"}

    workers = gpu.get("workers", {})

    summary = {}

    for name in ["spot_exec", "m5_exec", "m5_watch", "daystrom_exec", "daystrom_watch"]:
        w = workers.get(name, {})
        g = w.get("selected_gpu", {})

        summary[name] = {
            "model": g.get("name"),
            "free_vram_mb": g.get("vram_free_mb"),
            "total_vram_mb": g.get("vram_total_mb"),
            "temp_c": g.get("temp_c"),
            "power_w": g.get("power_w"),
        }

    return {
        "ok": True,
        "workers": summary,
    }

@APP.get("/api/job_queue")
def job_queue():
    try:
        r = requests.get(f"{SPOT_GATEWAY}/cluster/gpu_status", timeout=5).json()
    except Exception:
        return {"ok": False}

    workers = r.get("workers", {})

    queue = {}

    for name, w in workers.items():
        g = w.get("selected_gpu", {})
        util = g.get("util_gpu", "0")

        if util and util != "0 %":
            status = "busy"
        else:
            status = "idle"

        queue[name] = {
            "gpu": g.get("name"),
            "status": status
        }

    return {
        "ok": True,
        "workers": queue
    }

@APP.get("/api/job_stream/{job_id}")
def job_stream(job_id: str):

    stream_file = f"{JOBS_DIR}/{job_id}/stream.jsonl"

    def event_stream():
        pos = 0

        while True:
            if os.path.exists(stream_file):
                with open(stream_file, "r") as f:
                    f.seek(pos)

                    for line in f:
                        pos = f.tell()
                        yield f"data: {line.strip()}\n\n"

            time.sleep(0.1)

    return StreamingResponse(event_stream(), media_type="text/event-stream")

@APP.get("/", response_class=HTMLResponse)
def index(request: Request):
    return TEMPLATES.TemplateResponse(
        "index.html",
        {
            "request": request,
            "default_model": DEFAULT_MODEL,
            "fast_model": FAST_MODEL,
            "build_model": BUILD_MODEL,
            "repo_job_name": REPO_JOB_NAME,
        },
    )


@APP.get("/health")
def health():
    return {
        "ok": True,
        "service": "readyroom-ui",
        "default_model": DEFAULT_MODEL,
        "allowed_models": ALLOWED_MODELS,
        "repo_job_name": REPO_JOB_NAME,
        "ts": int(time.time()),
    }


@APP.get("/api/models")
def api_models():
    return {
        "ok": True,
        "default_model": DEFAULT_MODEL,
        "models": [
            {"id": FAST_MODEL, "label": f"Fast ({FAST_MODEL})", "mode": "fast"},
            {"id": BUILD_MODEL, "label": f"Build ({BUILD_MODEL})", "mode": "build"},
        ],
    }


@APP.get("/api/status")
def api_status():
    try:
        r = requests.get(f"{SPOT_BRAIN_URL}/cluster/status", timeout=10)
        r.raise_for_status()
        cluster = r.json()
    except Exception as exc:
        cluster = {"ok": False, "error": str(exc)}

    try:
        r2 = requests.get(f"{SPOT_BRAIN_URL}/cluster/gpu_status", timeout=10)
        r2.raise_for_status()
        gpu = r2.json()
    except Exception as exc:
        gpu = {"ok": False, "error": str(exc)}

    return {"ok": True, "cluster": cluster, "gpu": gpu, "ts": int(time.time())}


@APP.post("/api/run_job")
def get_fleet_summary() -> dict:
    try:
        r = requests.get("http://127.0.0.1:8790/api/fleet_summary", timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception:
        return {"ok": False, "workers": {}}


def choose_auto_model(prompt: str) -> str:
    p = (prompt or "").lower()

    code_words = [
        "python", "bash", "shell", "script", "code", "debug", "function",
        "fastapi", "javascript", "html", "css", "sql", "json", "yaml",
        "docker", "systemd", "regex", "api", "backend", "frontend"
    ]
    build_words = [
        "design", "architecture", "plan", "build", "reason", "analyze",
        "compare", "strategy", "refactor", "cluster", "scheduler"
    ]

    if any(w in p for w in code_words):
        return "deepseek-coder:6.7b"

    if any(w in p for w in build_words):
        return "qwen2.5:14b"

    return "llama3.1:8b"

    fleet = get_fleet_summary()
    workers = fleet.get("workers", {}) or {}

    candidates = []

    for name, info in workers.items():
        free_vram = info.get("free_vram_mb")
        try:
            free_vram = int(free_vram)
        except Exception:
            free_vram = 0

        if free_vram <= 0:
            continue

        candidates.append((name, free_vram))

    if not candidates:
        return None

    # Prefer stronger VRAM nodes for larger models
    if model == "qwen2.5:14b":
        preferred_order = ["daystrom_exec", "spot_exec", "m5_exec", "daystrom_watch", "m5_watch"]
    elif model == "deepseek-coder:6.7b":
        preferred_order = ["daystrom_exec", "spot_exec", "m5_exec", "daystrom_watch", "m5_watch"]
    else:
        preferred_order = ["spot_exec", "daystrom_exec", "m5_exec", "daystrom_watch", "m5_watch"]

    candidates_map = {name: free for name, free in candidates}

    for worker in preferred_order:
        if worker in candidates_map:
            return worker

    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates[0][0]

def api_run_job(body: JobBody):
    try:
        r = requests.post(
            f"{SPOT_BRAIN_URL}/cluster/auto_exec",
            json={"cmd": "run_job", "args": {"job": body.job, "params": body.params}},
            timeout=30,
        )
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail={"error": "run_job_failed", "detail": str(exc)},
        )

@APP.post("/api/run_llm")
def api_run_llm(body: PromptBody):
    requested_model = (body.model or "auto").strip()
    prompt = (body.prompt or "").strip()

    if not prompt:
        raise HTTPException(
            status_code=400,
            detail={"error": "missing_prompt"}
        )

    if requested_model in ("auto", "best", ""):
        model = choose_auto_model(prompt)
    else:
        model = requested_model

    if model not in ALLOWED_MODELS:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_model",
                "model": model,
                "allowed_models": ALLOWED_MODELS,
            },
        )

    chosen_worker = None
    if body.preferred_worker and body.preferred_worker not in ("", "auto", "best"):
        chosen_worker = body.preferred_worker

    payload = {
        "cmd": "run_job",
        "args": {
            "job": "llm_infer_stream",
            "params": {
                "prompt": prompt,
                "model": model,
                "system_prompt": body.system,
            },
        },
        "require_capability": "llm",
        "async_mode": True,
    }

    if chosen_worker:
        payload["preferred_worker"] = chosen_worker

    try:
        r = requests.post(f"{SPOT_BRAIN_URL}/cluster/auto_exec", json=payload, timeout=30)
        r.raise_for_status()
        data = r.json()
        return {
            "ok": True,
            "requested_model": requested_model,
            "resolved_model": model,
            "preferred_worker": body.preferred_worker,
            "resolved_worker": chosen_worker or data.get("picked_worker") or data.get("worker"),
            **data,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail={"error": "run_llm_failed", "detail": str(exc)},
        )

@APP.post("/api/repo_action")
def api_repo_action(body: RepoActionBody):
    cmd = (body.cmd or "").strip().lower()
    file = (body.file or "").strip()
    text = body.text or ""

    allowed_cmds = {"tree", "list", "read", "write", "append", "build"}
    if cmd not in allowed_cmds:
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_repo_cmd", "cmd": cmd, "allowed_cmds": sorted(allowed_cmds)},
        )

    if cmd in {"read", "write", "append"} and not file:
        raise HTTPException(
            status_code=400,
            detail={"error": "missing_file", "cmd": cmd},
        )

    params: dict[str, Any] = {"cmd": cmd}
    if file:
        params["file"] = file
    if cmd in {"write", "append"}:
        params["text"] = text

    try:
        r = requests.post(
            f"{SPOT_BRAIN_URL}/cluster/auto_exec",
            json={"cmd": "run_job", "args": {"job": REPO_JOB_NAME, "params": params}},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        return {"ok": True, "repo_cmd": cmd, **data}
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail={"error": "repo_action_failed", "detail": str(exc)},
        )


@APP.post("/api/generate_repo_draft")
def api_generate_repo_draft(body: GenerateRepoDraftBody):
    prompt = (body.prompt or "").strip()
    model = (body.model or DEFAULT_MODEL).strip()
    file = (body.file or "").strip()

    if not prompt:
        raise HTTPException(
            status_code=400,
            detail={"error": "missing_prompt"},
        )

    if model not in ALLOWED_MODELS:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_model",
                "model": model,
                "allowed_models": ALLOWED_MODELS,
            },
        )

    system = (
        "You are Spot, the engineering AI for Starfleet OS. "
        "Generate clean, practical repository content for the requested target file. "
        "Prefer markdown for docs, concise structure, and implementation-ready output. "
        "Do not include conversational framing, commentary, or explanations. "
        "Output only the file content."
    )

    if file:
        user_prompt = f"Target file: {file}\n\nTask:\n{prompt}"
    else:
        user_prompt = prompt

    chosen_worker = pick_worker_for_model(model)

    payload = {
        "cmd": "run_job",
        "args": {
            "job": "llm_infer_stream",
            "params": {
                "prompt": user_prompt,
                "model": model,
                "system_prompt": system,
            },
        },
        "require_capability": "llm",
        "async_mode": True,
    }

    if chosen_worker:
         payload["preferred_worker"] = chosen_worker

    try:
        r = requests.post(f"{SPOT_BRAIN_URL}/cluster/auto_exec", json=payload, timeout=30)
        r.raise_for_status()
        data = r.json()
        return {"ok": True, "requested_model": model, "target_file": file, **data}
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail={"error": "generate_repo_draft_failed", "detail": str(exc)},
        )


@APP.get("/api/job_stream/{job_name}/{job_id}")
def api_job_stream(job_name: str, job_id: str):
    stream_file = JOBS_OUT_ROOT / job_name / job_id / "stream.jsonl"
    rc_file = JOBS_OUT_ROOT / job_name / job_id / "rc.txt"

    def generate():
        pos = 0
        idle = 0
        while True:
            if stream_file.exists():
                with stream_file.open("r", encoding="utf-8", errors="replace") as f:
                    f.seek(pos)
                    for line in f:
                        line = line.strip()
                        if line:
                            yield f"data: {line}\n\n"
                    pos = f.tell()

            if rc_file.exists():
                idle += 1
                if idle > 5:
                    break

            time.sleep(0.2)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@APP.get("/api/job_result/{job_name}/{job_id}")
def api_job_result(job_name: str, job_id: str):
    job_dir = JOBS_OUT_ROOT / job_name / job_id
    result_file = job_dir / "result.json"
    meta_file = job_dir / "meta.json"
    rc_file = job_dir / "rc.txt"
    stdout_file = job_dir / "stdout.txt"
    stderr_file = job_dir / "stderr.txt"

    result: dict[str, Any] = {}
    meta: dict[str, Any] = {}

    if result_file.exists():
        result = json.loads(result_file.read_text(encoding="utf-8"))
    if meta_file.exists():
        meta = json.loads(meta_file.read_text(encoding="utf-8"))

    rc = rc_file.read_text(encoding="utf-8").strip() if rc_file.exists() else None
    eval_count = result.get("eval_count")
    eval_duration = result.get("eval_duration")
    tokens_per_sec = None

    if eval_count and eval_duration:
        try:
            tokens_per_sec = round(eval_count / (eval_duration / 1e9), 2)
        except ZeroDivisionError:
            tokens_per_sec = None

    return {
        "ok": True,
        "job_name": job_name,
        "job_id": job_id,
        "rc": rc,
        "model": result.get("model") or meta.get("model"),
        "node": meta.get("node"),
        "prompt_eval_count": result.get("prompt_eval_count"),
        "eval_count": eval_count,
        "total_duration": result.get("total_duration"),
        "eval_duration": eval_duration,
        "tokens_per_sec": tokens_per_sec,
        "start_iso": meta.get("start_iso"),
        "end_iso": meta.get("end_iso"),
        "total_wall_ns": meta.get("total_wall_ns"),
        "stdout": stdout_file.read_text(encoding="utf-8", errors="replace") if stdout_file.exists() else None,
        "stderr": stderr_file.read_text(encoding="utf-8", errors="replace") if stderr_file.exists() else None,
    }
