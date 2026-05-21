# Atomic Runtime Journal Writes

Purpose: provide safe helpers for runtime journal writes and recovery from malformed JSONL artifacts.

Capabilities:
- atomic JSON write using temp file, fsync, and rename
- append-only JSONL write using O_APPEND and fsync
- JSONL validation
- corruption copy/quarantine without deleting source
- targeted repair for known malformed monitor history JSONL files

Authority boundary:
- no execution authority is added
- no backup, review, rollback, or approval gate is bypassed
- corrupt source copies are preserved under watch/state/history/corrupt
- Spot Core remains sole executor

Commands:
- watch/journal/spot-atomic-journal.py append-jsonl --path FILE --json OBJECT
- watch/journal/spot-atomic-journal.py write-json --path FILE --json OBJECT
- watch/journal/spot-atomic-journal.py validate-jsonl --path FILE
- watch/journal/spot-atomic-journal.py quarantine-jsonl --path FILE
- watch/journal/spot-journal-repair.py
- watch/journal/spot-journal-validate.py

Known repaired files:
- watch/state/history/monitor-alert-transitions.jsonl
- watch/state/history/monitor-summary.jsonl
