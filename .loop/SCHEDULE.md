# SCHEDULE

## Triggers
- Manual: a new demand is placed in `.loop/specs/` or requested by the user.
- After each builder task: tester_judge runs.

## Limits
- Max 5 attempts per task.
- Max 3 full cycles per demand before escalating to the user.
- Stop criterion: `aif check --json` -> `{"ok": true, "errors": []}`.
