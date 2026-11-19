# Changelog

## 0.1.0 — local preview

- Remove Capo's fixed two-Worker default; schedule independent tasks within observed host capacity and explicit user limits while retaining model budgets, scoped pauses and write-domain checks.
- Introduce portable routine, complex and analyst roles with entrypoint-specific capability checks.
- Apply advanced Worker budgets to inheritance, fallback and wakeup paths; unknown models are not reported as verified zero-cost usage.
- Centralize dispatch and tree-wide concurrency reservations at the Router.
- Separate message acknowledgement, Worker submission and version-bound acceptance evidence.
- Preserve scoped pause, safe write-domain handoff and stale-assignment rules.
- Add synthetic examples, offline validation, controlled isolation experiment and minimal CI.

This is a prompt-based coordination protocol. It does not add runtime locks, operating-system isolation or a background scheduler.
