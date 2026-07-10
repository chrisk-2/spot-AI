#!/usr/bin/env bash
set -u

MEMORY_ROOT="${SPOT_MEMORY_ROOT:-/mnt/collective/memory/spot}"

CATEGORIES=(
  events
  infrastructure
  operator
  strategy
)

echo "===== SPOT MEMORY STATUS ====="
echo "timestamp=$(date -Is)"
echo "host=$(hostname)"
echo "mode=read_only"
echo "mutation_authority=false"
echo "memory_root=$MEMORY_ROOT"
echo

if [[ ! -d "$MEMORY_ROOT" ]]; then
  echo "memory_state=NOT-INITIALIZED"
  echo "overall=EMPTY"
  echo "mutation_performed=false"
  exit 0
fi

present=0
records=0
checksum_pass=0
checksum_warn=0

for category in "${CATEGORIES[@]}"; do
  root="$MEMORY_ROOT/$category"
  index="$root/index.jsonl"

  echo "===== CATEGORY $category ====="

  if [[ ! -d "$root" ]]; then
    echo "state=NOT-PRESENT"
    echo
    continue
  fi

  present=$((present + 1))

  if [[ -f "$index" ]]; then
    count="$(wc -l <"$index")"
    latest="$(tail -n 1 "$index")"

    echo "state=PRESENT"
    echo "index=$index"
    echo "records=$count"
    echo "latest=$latest"

    records=$((records + count))
  else
    echo "state=PRESENT-NO-INDEX"
  fi

  latest_checksum="$(
    find "$root" \
      -maxdepth 1 \
      -type f \
      -name '*.sha256' \
      -printf '%T@ %p\n' 2>/dev/null |
      sort -nr |
      awk 'NR == 1 {$1=""; sub(/^ /, ""); print}'
  )"

  if [[ -n "$latest_checksum" ]]; then
    if sha256sum -c "$latest_checksum" >/dev/null 2>&1; then
      echo "latest_checksum=PASS"
      checksum_pass=$((checksum_pass + 1))
    else
      echo "latest_checksum=WARN"
      checksum_warn=$((checksum_warn + 1))
    fi
  else
    echo "latest_checksum=NOT-PRESENT"
  fi

  echo
done

echo "summary_categories=${#CATEGORIES[@]}"
echo "summary_present=${present}"
echo "summary_records=${records}"
echo "summary_checksum_pass=${checksum_pass}"
echo "summary_checksum_warn=${checksum_warn}"

if (( checksum_warn > 0 )); then
  echo "overall=DEGRADED"
elif (( present == ${#CATEGORIES[@]} )); then
  echo "overall=HEALTHY"
else
  echo "overall=PARTIAL"
fi

echo "mutation_performed=false"
