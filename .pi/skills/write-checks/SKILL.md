---
name: write-checks
description: Run a mandatory CashBuffer brainstorming session before drafting approved acceptance checks.
disable-model-invocation: false
user-invocable: true
argument-hint: "<feature request>"
---

# CashBuffer write checks

Input: feature request.

## Non-negotiable me session
1. Read `.pi/skills/project-context/SKILL.md` and inspect relevant existing architecture. Do not create or modify tests.
2. Start a visible **Me Session** in chat. Ask the user focused questions about scope, money precision/currency, tenant isolation, authorization, invalid input, persistence, retries/idempotency, external-provider failures, and observability. Gather edge cases before drafting checks.
3. Present a draft checklist in chat, including scope exclusions and unresolved assumptions.
4. Stop and wait for explicit user approval. Do not write `pending_checks.md` before approval. “Looks good” or equivalent must be explicit approval; silence is not approval.
5. After approval, write only `pending_checks.md` at repository root. Never write production code, tests, fixtures, migrations, or any other file.

## Approved checklist format
```md
# Checks: <feature name>

## Scope
- <included behavior>
- <excluded behavior>

## Checks
- [ ] C001 — <observable deterministic behavior and exact verification>

## Architecture checks
- [ ] A001 — <CashBuffer route/service/data-boundary verification>

## Failure and security checks
- [ ] S001 — <currency, authorization, tenant isolation, validation, persistence, or provider-error verification>

## Test commands
- `<smallest relevant existing command>`
```

Checks must be independently pass/fail, observable, deterministic, and tailored to CashBuffer. Cover happy path, invalid input, authorization and tenant isolation, persistence, money precision, external failure paths, and architecture boundaries when relevant. Never invent a framework or command not supported by the repository.
