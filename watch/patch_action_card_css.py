#!/usr/bin/env python3
"""
Append SpotActionCard CSS additions to App.css:
- .spot-action-warn border support (was color-only, now also shows border)
- .spot-action-params  — container for extra params block
- .spot-action-params-label — "PARAMS" section header
- .spot-action-param-row — indented param rows
"""
import sys

TARGET = "/home/ogre/spot-stack/starfleet-ui/src/App.css"

APPEND = """
/* ══ SPOT ACTION CARD — params block & risk border fix ══════ */
.spot-action-warn {
  font-size: 10px;
  font-family: 'Rajdhani', sans-serif;
  font-weight: 700;
  letter-spacing: 1px;
  padding: 4px 8px;
  border-radius: 3px;
  border: 1px solid;
  margin-bottom: 6px;
  display: inline-block;
}
.spot-action-params {
  margin-top: 6px;
  padding-top: 6px;
  border-top: 1px solid #0a2040;
}
.spot-action-params-label {
  font-family: 'Orbitron', monospace;
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 2px;
  color: #2a5a8a;
  margin-bottom: 4px;
}
.spot-action-param-row span {
  color: #3a6a8a !important;
  font-style: italic;
}
.spot-action-param-row b {
  color: #88aacc !important;
  word-break: break-all;
}
"""

with open(TARGET, "r") as f:
    content = f.read()

if ".spot-action-params" in content:
    print("SKIP: .spot-action-params already present in App.css")
    sys.exit(0)

with open(TARGET, "a") as f:
    f.write(APPEND)

print("OK: App.css updated with SpotActionCard params/warn styles")
