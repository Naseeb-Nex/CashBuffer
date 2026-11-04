---
name: auto-loop
description: Analyzes loop_results.log failures and appends learned rules to the root program.md.
---

# Auto-Loop

This skill runs automatically after a build loop completes or on manual trigger. It analyzes `loop_results.log` to find patterns in feature builder failures and updates `program.md` with new explicit rules to help future loops.

## Operation

1. If `loop_results.log` does not exist, stop.
2. Read `program.md`. If it does not exist, stop.
3. Parse the log file to identify:
   - Recurring failures (same error pattern appearing multiple times)
   - Checks that required multiple rounds to pass
   - Structural or process mistakes that caused repeated attempts
4. If any learning patterns are found:
   - Append a new rule or clarification to the "Fixed Rules" or "How to work" section in `program.md`
   - Ensure the new rule is specific and actionable
5. Output a "Learning Report" to the terminal:
   - What mistake or pattern was identified
   - What rule was added to `program.md`

## Restrictions

- Never write, edit, or touch any file under `./locked_checks/`.
- Never modify application code or tests.
- Only modify `program.md`.

## Manual trigger

Run:
\`\`\`bash
Use this procedure from repository root: read `loop_results.log`, then update only `program.md`.
\`\`\`

The skill can also run automatically after a successful build loop completes.
