# Module — Review Governance Hardening

## Scope

This module normalizes review operator visibility and prevents transient local reviewer latency from blocking unrelated module commits.

## Completed

- Added review health command surface.
- Added review escalation command surface.
- Added OpenAI external review gate visibility.
- Preserved local-first review policy.
- Preserved worker-05 review and worker-06 escalation model.
- Converted transient `/review/local` timeout from hard validation failure to warning.

## Review Surface

Commands:

    watch/module/spot-module.sh operator review
    watch/module/spot-module.sh operator review-health
    watch/module/spot-module.sh operator review-escalate
    watch/module/spot-module.sh operator review-openai
    watch/module/spot-module.sh operator review-journal
    watch/module/spot-module.sh operator review-journal-validate

## Policy

- Worker-05 remains primary local reviewer.
- Worker-06 remains local escalation path.
- OpenAI remains approval-required external review only.
- Review does not grant mutation authority.
- Spot Core remains sole enforcement authority.
