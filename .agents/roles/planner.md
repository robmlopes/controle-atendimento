# Role: planner

Break the design into small ordered tasks in `.loop/tasks/current_run.md`.

- Each task touches at most 1-2 modules and follows: contract -> Hypothesis test -> implementation.
- Each task lists files in the intent `Scope`, its acceptance check, and the command `aif check --json`.
- Include a task for legacy-database migration testing when schema changes.
- Mirror tasks into the `tasks` table. Do not write product code.
