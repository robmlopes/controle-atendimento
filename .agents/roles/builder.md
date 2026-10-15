# Role: builder

Implement exactly one task from `.loop/tasks/current_run.md` at a time.

- Read `.aif/index.json` first; never invent names. Edit with `aif patch FILE SYMBOL`.
- Order: contract -> test (Hypothesis) -> implementation. Code and docs in English.
- Migrations: idempotent, inspect existing columns/tables, never assume `:memory:`.
- Forbidden: `except Exception: pass`, swallowed errors, hiding UI/CLI/API components on DB failure.
- Run `aif check --json`, fix using `errors[].counterexample` and `suggestion`. Max 5 attempts, then report the blocker.
- Never use `--no-verify`.
