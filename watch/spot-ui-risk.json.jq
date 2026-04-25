def risk_score($s; $h; $r; $stale):
  def lastn($a; $n): ($a // [] | if length > $n then .[(length-$n):] else . end);
  def increasing($a): ($a|length) >= 3 and ($a[-1] > $a[-2]) and ($a[-2] > $a[-3]);
  def age_sec: ((now | floor) - (($h.last_generated_at // $s.generated_at) | fromdateiso8601? // (now|floor)));
  def rem_entries: ($r | to_entries | map(select(.key != "_meta")));
  def worker_fail_count: (($s.workers // []) | map(select(.ok != true)) | length);
  def worker_warn_count: (($s.workers // []) | map(select(.severity == "warn")) | length);
  def quarantine_count: (rem_entries | map(select(.value.quarantined == true)) | length);
  def remediation_violation_count: (rem_entries | map((.value.violation_count_window // 0)) | add // 0);
  def nonok_count: (($h.trends.banner_statuses // []) | lastn(.;5) | map(select(. != "OK")) | length);
  def points:
    0
    + (if ($s.core.ok != true) then 40 else 0 end)
    + (if ($s.banner.status == "ALERT") then 30 elif ($s.banner.status == "WARN") then 12 else 0 end)
    + (if ($s.routing.status == "FAIL") then 30 elif ($s.routing.status == "WARN") then 10 else 0 end)
    + (($s.routing.violations // 0) * 4)
    + (($s.routing.fallbacks // 0) * 2)
    + (worker_fail_count * 20)
    + (worker_warn_count * 8)
    + (quarantine_count * 15)
    + (remediation_violation_count * 3)
    + (if age_sec > $stale then 15 else 0 end)
    + (if increasing($h.trends.routing_fallbacks // []) then 8 else 0 end)
    + (if increasing($h.trends.routing_violations // []) then 12 else 0 end)
    + (if nonok_count >= 3 then 10 else 0 end);
  points as $p
  | {
      score: ([$p,100] | min),
      level: (if $p >= 75 then "CRITICAL" elif $p >= 45 then "HIGH" elif $p >= 20 then "ELEVATED" else "NORMAL" end),
      factors: [
        (if ($s.core.ok != true) then "core health failing" else empty end),
        (if ($s.banner.status != "OK") then "incident banner=" + $s.banner.status else empty end),
        (if ($s.routing.status != "OK") then "routing status=" + $s.routing.status else empty end),
        (if ($s.routing.violations // 0) > 0 then "routing violations=" + (($s.routing.violations // 0)|tostring) else empty end),
        (if ($s.routing.fallbacks // 0) > 0 then "routing fallbacks=" + (($s.routing.fallbacks // 0)|tostring) else empty end),
        (if worker_fail_count > 0 then "worker failures=" + (worker_fail_count|tostring) else empty end),
        (if worker_warn_count > 0 then "worker warnings=" + (worker_warn_count|tostring) else empty end),
        (if quarantine_count > 0 then "active quarantines=" + (quarantine_count|tostring) else empty end),
        (if remediation_violation_count > 0 then "remediation violation memory=" + (remediation_violation_count|tostring) else empty end),
        (if age_sec > $stale then "publisher stale=" + (age_sec|tostring) + "s" else empty end),
        (if increasing($h.trends.routing_fallbacks // []) then "fallbacks rising" else empty end),
        (if increasing($h.trends.routing_violations // []) then "violations rising" else empty end),
        (if nonok_count >= 3 then "persistent non-OK banner" else empty end)
      ]
    };

risk_score($s; $h; $r; $stale)
