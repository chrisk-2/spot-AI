#!/usr/bin/env python3
# Starfleet Control Panel (Authed, CORS, RBAC, Proxy-Ready)
import os, subprocess, json, time
from functools import wraps
from flask import Flask, request, jsonify, send_from_directory, make_response

TOKEN_SUPER = os.getenv("CONTROL_PANEL_TOKEN", "changeme")
TOKEN_VIEW  = os.getenv("CONTROL_PANEL_VIEW_TOKEN", "")
HOST = os.getenv("STARFLEET_HOST", "localhost")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROLES_FILE = os.getenv("STARFLEET_ROLES_FILE", "/etc/starfleet/roles.json")

app = Flask(__name__, static_folder=BASE_DIR, static_url_path="")

def _bearer_token():
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth.split(" ", 1)[1].strip()
    return request.args.get("token", "")

def _user_from_proxy():
    return request.headers.get("X-Forwarded-User", "")

def _roles_db():
    try:
        with open(ROLES_FILE, "r") as f:
            return json.load(f)
    except Exception:
        pass
    db = {"users":{}, "tokens":{}}
    if TOKEN_SUPER:
        db["tokens"]["SUPER"] = {"value": TOKEN_SUPER, "roles": ["*"]}
    if TOKEN_VIEW:
        db["tokens"]["VIEW"] = {"value": TOKEN_VIEW, "roles": ["theme","health"]}
    db["rules"] = {"default": []}
    return db

def _resolve_roles():
    db = _roles_db()
    token = _bearer_token()
    user = _user_from_proxy()
    for name, entry in db.get("tokens", {}).items():
        if token and entry.get("value") == token:
            return entry.get("roles", [])
    if user:
        roles = db.get("users", {}).get(user, [])
        if roles:
            return roles
    return db.get("rules", {}).get("default", [])

def require_roles(*needed):
    def deco(fn):
        from functools import wraps
        @wraps(fn)
        def wrapper(*a, **kw):
            roles = _resolve_roles()
            if "*" in roles or any(n in roles for n in needed):
                return fn(*a, **kw)
            return jsonify({"error":"forbidden","need":needed,"have":roles}), 403
        return wrapper
    return deco

def _run(cmd):
    import subprocess
    try:
        out = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, timeout=120)
        return out.decode().strip()
    except subprocess.CalledProcessError as e:
        return f"ERROR: {e.output.decode(errors='ignore').strip()}"
    except Exception as e:
        return f"ERROR: {e}"

@app.after_request
def add_cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return resp

@app.route("/<path:_p>", methods=["OPTIONS"])
def options_passthru(_p):
    from flask import make_response
    return make_response(("", 204))

@app.get("/")
def index():
    return send_from_directory(BASE_DIR, "control_panel_lcars_embed.html")

@app.before_request
def gate():
    from flask import request, jsonify
    if request.method == "OPTIONS":
        return None
    if request.path in ("/", "/index.html", "/control_panel_lcars_embed.html"):
        return None
    if not TOKEN_SUPER:
        return jsonify({"error":"panel not configured"}), 503
    return None

@app.get("/ping")
def ping():
    return jsonify({"ok": True, "time": time.time()})

@app.get("/version")
def version():
    return jsonify({"ok": True,"component":"starfleet-control-panel","features":["auth","cors","rbac","stealth","theme","health","snapshot"],"base_dir": BASE_DIR})

@app.post("/stealth/on")
@require_roles("stealth")
def stealth_on():
    res = _run("systemctl start section31-stealth.service || true")
    return jsonify({"ok": True, "action": "stealth_on", "result": res})

@app.post("/stealth/off")
@require_roles("stealth")
def stealth_off():
    res = _run("systemctl stop section31-stealth.service || true")
    return jsonify({"ok": True, "action": "stealth_off", "result": res})

@app.post("/grafana/dark")
@require_roles("theme")
def grafana_dark():
    script = os.path.join(BASE_DIR, "grafana_theme_dark.sh")
    res = _run(f"bash {script}")
    return jsonify({"ok": True, "action": "grafana_dark", "result": res})

@app.post("/grafana/light")
@require_roles("theme")
def grafana_light():
    script = os.path.join(BASE_DIR, "grafana_theme_light.sh")
    res = _run(f"bash {script}")
    return jsonify({"ok": True, "action": "grafana_light", "result": res})

@app.post("/health")
@require_roles("health")
def health():
    script = os.path.join(BASE_DIR, "health_report.sh")
    host = HOST
    try:
        if request.is_json and "host" in (request.get_json(silent=True) or {}):
            host = request.get_json().get("host") or HOST
    except Exception:
        pass
    res = _run(f"bash {script} {host}")
    return jsonify({"ok": True, "action": "health", "host": host, "result": res, "report": "/mnt/data/health_report.txt"})

@app.post("/snapshot")
@require_roles("snapshot")
def snapshot():
    script = os.path.join(BASE_DIR, "full_system_snapshot.sh")
    res = _run(f"bash {script}")
    return jsonify({"ok": True, "action": "snapshot", "result": res})

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5080, debug=False)
