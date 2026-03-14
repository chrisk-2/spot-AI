import os, time, subprocess
import psutil
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

APP = FastAPI(title="Spot Worker")

EXEC_TOKEN = os.environ.get("EXEC_TOKEN", "changeme")

ALLOWED = {
    "uptime": ["bash","-lc","uptime"],
    "nvidia_smi": ["bash","-lc","nvidia-smi || true"],
    "df": ["bash","-lc","df -h"],
    "free": ["bash","-lc","free -h"],
    "lscpu": ["bash","-lc","lscpu"],
}

START = time.time()

class ExecReq(BaseModel):
    token: str
    cmd: str

@APP.get("/health")
def health():
    return {"ok": True, "uptime_sec": int(time.time() - START)}

@APP.get("/status")
def status():
    return {
        "cpu_percent": psutil.cpu_percent(interval=0.2),
        "ram_percent": psutil.virtual_memory().percent,
        "uptime_sec": int(time.time() - START)
    }

@APP.post("/exec")
def exec_cmd(req: ExecReq):
    if req.token != EXEC_TOKEN:
        raise HTTPException(403, "Bad token")
    if req.cmd not in ALLOWED:
        raise HTTPException(400, f"Command not allowed. Allowed: {sorted(ALLOWED.keys())}")
    p = subprocess.run(ALLOWED[req.cmd], capture_output=True, text=True)
    return {"ok": True, "rc": p.returncode, "stdout": p.stdout, "stderr": p.stderr}
