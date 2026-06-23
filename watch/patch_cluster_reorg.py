#!/usr/bin/env python3
import json, shutil, ast
from pathlib import Path

CFG = Path("/home/ogre/spot-stack/spot-core/config/cluster_config.json")
APP = Path("/home/ogre/spot-stack/spot-core/spotcore/app.py")
shutil.copy2(CFG, CFG.with_suffix(".json.pre-reorg"))
cfg = json.loads(CFG.read_text())

# Canonical ownership table
cfg["role_owners_canonical"] = {
    "general":   "spot-worker-01",
    "utility":   "spot-worker-02",
    "coding":    "spot-worker-03",
    "heavy":     "spot-worker-04",
    "review":    "spot-worker-05",
    "reasoning": "spot-worker-06",
}
cfg["role_standin_priority"] = {
    "reasoning": ["spot-worker-05", "spot-worker-04"],
    "heavy":     ["spot-worker-05", "spot-worker-01"],
    "review":    ["spot-worker-06", "spot-worker-04"],
    "coding":    ["spot-worker-03"],
    "general":   ["spot-worker-01", "spot-worker-03"],
    "utility":   ["spot-worker-02"],
}

# W-02: TITAN Xp gets general burst
cfg["workers"]["spot-worker-02"]["class_limits"]["general"] = 1
cfg["workers"]["spot-worker-02"]["secondary_roles"] = ["watcher", "general"]
cfg["workers"]["spot-worker-02"]["gpu_routes"]["gpu0"] = {
    "label": "TITAN Xp 12GB",
    "max_total": 1,
    "classes": ["utility", "general"],
    "model_limits": {"mistral:7b": 1},
    "model_preferences": {"utility": ["mistral:7b"], "general": ["mistral:7b"]}
}
cfg["workers"]["spot-worker-02"]["gpu_routes"]["gpu1"] = {
    "label": "Quadro M4000 8GB",
    "max_total": 1,
    "classes": ["utility", "watcher"],
    "model_limits": {"bge-m3:latest": 1, "nomic-embed-text:latest": 1},
    "model_preferences": {"utility": ["bge-m3:latest", "nomic-embed-text:latest"], "watcher": ["bge-m3:latest"]}
}
if "spot-worker-02" not in cfg["role_priority"]["general"]:
    cfg["role_priority"]["general"].append("spot-worker-02")

# W-04: Add reasoning fallback with 30b models
cfg["workers"]["spot-worker-04"]["class_limits"]["reasoning"] = 1
cfg["workers"]["spot-worker-04"]["secondary_roles"] = ["reasoning"]
cfg["workers"]["spot-worker-04"]["gpu_routes"]["gpu0"]["classes"] = ["heavy", "reasoning"]
cfg["workers"]["spot-worker-04"]["gpu_routes"]["gpu0"]["model_preferences"]["reasoning"] = [
    "qwen3:30b-a3b", "mistral-small:24b", "qwen2.5:14b"
]
if "spot-worker-04" not in cfg["role_priority"]["reasoning"]:
    cfg["role_priority"]["reasoning"].append("spot-worker-04")

# W-05: reasoning stand-in owner, both P100 lanes
cfg["workers"]["spot-worker-05"]["primary_role"] = "reasoning"
cfg["workers"]["spot-worker-05"]["secondary_roles"] = ["heavy", "review"]
cfg["workers"]["spot-worker-05"]["max_total"] = 2
cfg["workers"]["spot-worker-05"]["class_limits"].update({"reasoning": 2, "review": 1, "heavy": 1})
cfg["workers"]["spot-worker-05"]["gpu_routes"]["gpu0"] = {
    "label": "Tesla P100 16GB (#1)",
    "max_total": 1,
    "classes": ["reasoning", "heavy", "review"],
    "model_limits": {"deepseek-r1:14b": 1, "deepseek-r1:32b": 1, "qwen2.5:32b": 1, "qwen2.5:14b": 1, "qwen2.5-coder:14b": 1, "qwen2.5-coder:32b": 1},
    "model_preferences": {
        "reasoning": ["deepseek-r1:14b", "qwen2.5:32b", "qwen2.5:14b"],
        "heavy":     ["qwen2.5:32b", "qwen2.5:14b"],
        "review":    ["qwen2.5-coder:32b", "deepseek-r1:14b", "qwen2.5:32b"],
    }
}
cfg["workers"]["spot-worker-05"]["gpu_routes"]["gpu1"] = {
    "label": "Tesla P100 16GB (#2)",
    "max_total": 1,
    "classes": ["reasoning", "heavy", "review"],
    "model_limits": {"deepseek-r1:14b": 1, "deepseek-r1:32b": 1, "qwen2.5:32b": 1, "qwen2.5:14b": 1, "qwen2.5-coder:14b": 1, "qwen2.5-coder:32b": 1},
    "model_preferences": {
        "reasoning": ["deepseek-r1:14b", "qwen2.5:32b", "qwen2.5:14b"],
        "heavy":     ["qwen2.5:32b", "qwen2.5:14b"],
        "review":    ["qwen2.5-coder:14b", "deepseek-r1:14b", "qwen2.5:14b"],
    }
}
rp = cfg["role_priority"]["reasoning"]
cfg["role_priority"]["reasoning"] = ["spot-worker-05"] + [w for w in rp if w != "spot-worker-05"]

CFG.write_text(json.dumps(cfg, indent=2))
print("cluster_config.json written")

# Patch ROLE_OWNERS in app.py
src = APP.read_text()
old = '\nROLE_OWNERS: dict[str, str] = {\n    "general": "spot-worker-01",\n    "utility": "spot-worker-02",\n    "coding": "spot-worker-03",\n    "heavy": "spot-worker-04",\n    "reasoning": "spot-worker-06"\n}'
new = '\nROLE_OWNERS: dict[str, str] = {\n    "general": "spot-worker-01",\n    "utility": "spot-worker-02",\n    "coding": "spot-worker-03",\n    "heavy": "spot-worker-04",\n    "review": "spot-worker-05",\n    "reasoning": "spot-worker-05",  # stand-in: canonical owner is spot-worker-06\n}'
assert old in src, "ROLE_OWNERS anchor not found"
src = src.replace(old, new, 1)
ast.parse(src)
APP.write_text(src)
print("app.py ROLE_OWNERS patched")
print("Done")
