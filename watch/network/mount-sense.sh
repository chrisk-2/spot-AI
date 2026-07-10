#!/usr/bin/env bash
set -u

TARGETS=(
  /mnt/collective
  /mnt/unimatrix6
  /mnt/ai-data
)

present=0
missing=0
warn=0

echo "===== SPOT STORAGE AND MOUNT SENSE ====="
echo "timestamp=$(date -Is)"
echo "host=$(hostname)"
echo "mode=read_only"
echo "mutation_authority=false"
echo

for target in "${TARGETS[@]}"; do
  echo "===== TARGET ${target} ====="

  if [[ ! -e "$target" ]]; then
    echo "state=NOT-PRESENT"
    missing=$((missing + 1))
    echo
    continue
  fi

  present=$((present + 1))

  if findmnt -rn -T "$target" >/dev/null 2>&1; then
    source="$(findmnt -rn -T "$target" -o SOURCE 2>/dev/null || true)"
    fstype="$(findmnt -rn -T "$target" -o FSTYPE 2>/dev/null || true)"
    options="$(findmnt -rn -T "$target" -o OPTIONS 2>/dev/null || true)"
    mountpoint="$(findmnt -rn -T "$target" -o TARGET 2>/dev/null || true)"

    echo "state=MOUNTED"
    echo "source=${source}"
    echo "filesystem=${fstype}"
    echo "mountpoint=${mountpoint}"
    echo "options=${options}"

    case ",${options}," in
      *,ro,*)
        echo "access_mode=READ-ONLY"
        ;;
      *,rw,*)
        echo "access_mode=READ-WRITE"
        ;;
      *)
        echo "access_mode=UNKNOWN"
        ;;
    esac

    timeout 5 stat "$target" >/dev/null 2>&1
    stat_rc=$?

    if (( stat_rc == 0 )); then
      echo "metadata_probe=PASS"
    else
      echo "metadata_probe=WARN"
      echo "metadata_probe_exit=${stat_rc}"
      warn=$((warn + 1))
    fi

    timeout 5 find "$target" \
      -mindepth 1 \
      -maxdepth 1 \
      -print \
      -quit >/dev/null 2>&1

    list_rc=$?

    if (( list_rc == 0 )); then
      echo "bounded_directory_probe=PASS"
    else
      echo "bounded_directory_probe=WARN"
      echo "bounded_directory_probe_exit=${list_rc}"
      warn=$((warn + 1))
    fi

    df -hPT "$target" 2>/dev/null || true
  else
    echo "state=PATH-PRESENT-NOT-MOUNTED"
    warn=$((warn + 1))
  fi

  echo
done

echo "summary_present=${present}"
echo "summary_missing_optional=${missing}"
echo "observations=${warn}"

if (( warn == 0 )); then
  echo "overall=HEALTHY"
else
  echo "overall=DEGRADED"
fi

echo "write_probe_performed=false"
echo "mutation_performed=false"
