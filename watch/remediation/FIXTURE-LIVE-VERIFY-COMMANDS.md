# Fixture Live Verify Commands

## Pre-activation
test -s watch/remediation/spot-remediation-fixture.sh
test -s watch/remediation/spot-remediation-fixture.service
bash -n watch/remediation/spot-remediation-fixture.sh
sha256sum -c watch/review/bundles/phase235a-fixture-implementation-review-bundle-*.md.sha256
spot validate

## Post-activation
systemctl is-active --quiet spot-remediation-fixture.service || systemctl status spot-remediation-fixture.service --no-pager
test -s /tmp/spot-remediation-fixture.heartbeat
jq -e '.fixture=="spot-remediation-fixture" and .status=="ok"' /tmp/spot-remediation-fixture.heartbeat
systemctl show spot-remediation-fixture.service -p Result -p ExecMainStatus --no-pager
spot validate
