---
name: build
description: Build orchestrator for CashBuffer. Reads locked checks, invokes feature-builder, runs tests, logs to loop_results.log, and handles auto-loop on failure.
argument-hint: "<feature-slug>"
---

# Build Orchestrator

1. Read `locked_checks/<feature-slug>.md`.
2. Invoke `feature-builder` agent round with `program.md` and the locked checks.
3. Run verification/test commands specified in the locked check.
4. Append outcome to `loop_results.log`.
5. If tests fail, invoke `auto-loop` to analyze and update `program.md`.
