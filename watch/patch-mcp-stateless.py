#!/usr/bin/env python3
"""Patch spot_mcp_wrapper.py to enable stateless_http=True.

Fixes session-affinity drops across the Cloudflare tunnel ('Session terminated').
Surgical: only adds the stateless_http=True kwarg to the FastMCP(...) constructor.
"""
import ast
import shutil
import sys
import time

TARGET = "/home/ogre/spot-mcp/spot_mcp_wrapper.py"

OLD = """mcp = FastMCP(
    APP_NAME,
    json_response=True,
    transport_security=TransportSecuritySettings("""

NEW = """mcp = FastMCP(
    APP_NAME,
    json_response=True,
    stateless_http=True,
    transport_security=TransportSecuritySettings("""

def main():
    with open(TARGET, "r") as f:
        src = f.read()

    if "stateless_http=True" in src:
        print("ALREADY PATCHED: stateless_http=True is already present. No change.")
        return 0

    count = src.count(OLD)
    if count != 1:
        print(f"ABORT: expected exactly 1 match of constructor anchor, found {count}.")
        print("File may have changed; not patching blindly.")
        return 1

    patched = src.replace(OLD, NEW)

    # Validate the patched source parses as Python before writing anything.
    try:
        ast.parse(patched)
    except SyntaxError as e:
        print(f"ABORT: patched source failed ast.parse(): {e}")
        return 1

    # Backup, then write.
    backup = f"{TARGET}.bak-{int(time.time())}"
    shutil.copy2(TARGET, backup)
    with open(TARGET, "w") as f:
        f.write(patched)

    print(f"OK: patched {TARGET}")
    print(f"Backup written to {backup}")
    print("stateless_http=True inserted into FastMCP constructor.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
