#!/usr/bin/env python3
from pathlib import Path
import re
import shutil
import time

repo = Path.cwd()
path = repo / "spot-core" / "spotcore" / "spot-proactive.py"
marker = "SPOT OUTCOME RESOLVER HOOK BEGIN"

if not path.exists():
    print(f"RESULT: SKIP missing={path}")
    raise SystemExit(0)

text = path.read_text(encoding="utf-8")
if marker in text:
    print("RESULT: PASS proactive already patched")
    raise SystemExit(0)

stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
shutil.copy2(path, path.with_suffix(path.suffix + f".bak-outcome-{stamp}"))

hook = r'''
# --- SPOT OUTCOME RESOLVER HOOK BEGIN ---
def spot_outcome_resolver_tick():
    """Deferred outcome resolver. Safe: appends outcome_update records only."""
    import subprocess
    import sys
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[2]
    resolver = repo_root / "watch" / "outcomes" / "spot-outcome-resolve.py"
    if resolver.exists():
        subprocess.run(
            [sys.executable, str(resolver), "--min-age-seconds", "180", "--limit", "25"],
            cwd=str(repo_root),
            timeout=45,
            check=False
        )
# --- SPOT OUTCOME RESOLVER HOOK END ---
'''

inserted = False

# Prefer inserting the resolver call before an existing 5-minute sleep in the loop.
pattern = re.compile(r"(?m)^([ \t]*)(time\.sleep\(\s*300\s*\)|sleep\(\s*300\s*\))")
def repl(m):
    global inserted
    inserted = True
    indent = m.group(1)
    return f"{indent}spot_outcome_resolver_tick()\n{m.group(0)}"

new_text = pattern.sub(repl, text, count=1)

if not inserted:
    new_text = text.rstrip() + "\n\n" + hook + "\n"
    print("RESULT: WARN hook added but no 300-second sleep found for automatic tick insertion")
else:
    # Put hook before first if __main__ when possible, otherwise append.
    idx = new_text.find('if __name__ == "__main__"')
    if idx >= 0:
        new_text = new_text[:idx].rstrip() + "\n\n" + hook + "\n\n" + new_text[idx:]
    else:
        new_text = new_text.rstrip() + "\n\n" + hook + "\n"
    print("RESULT: PASS proactive resolver tick inserted")

path.write_text(new_text, encoding="utf-8")
