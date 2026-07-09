#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

wrapper = Path.home() / "spot-mcp" / "spot_mcp_wrapper.py"
out = Path.home() / "spot-stack" / "spot-core" / "config" / "unifi_site.json"

spec = importlib.util.spec_from_file_location("spot_mcp_wrapper_for_site_discovery", wrapper)
if spec is None or spec.loader is None:
    raise SystemExit(f"FAIL: cannot load {wrapper}")

mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

site = None
if hasattr(mod, "_spot_unifi_site_id"):
    site = mod._spot_unifi_site_id()

if not site:
    site = "default"

out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps({"site": site, "source": "unifi-site-discover"}, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"site": site, "config": str(out)}, indent=2))
