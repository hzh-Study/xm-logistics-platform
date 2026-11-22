## Agent skills

### Issue tracker

Issues live in this repo's GitHub Issues (`hzh-Study/xm-logistics-platform`), managed with the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

The five canonical triage roles are used verbatim as label strings. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one root `GLOSSARY.md` plus `docs/adr/`. See `docs/agents/domain.md`.

### Code review

Reviewing code? Read `CODING_STANDARDS.md` for the cross-file judgement calls; mechanical rules are enforced by tests, not listed there.

## Verify migrations

Before reporting any SQLite schema/migration change done, run both from `backend/`: `python -m pytest -q tests/test_migration_integrity.py` (block order, upgrade paths, snapshot immutability, banned source patterns) and the full `python -m pytest -q` (routers/services too).

## Scripting

Automation, startup, build and schema scripts are `.py` files run with `python`; no hand-written `.bat`/`.cmd` or shell script files. `npm run ...` commands and one-line shell commands are the exception. Declare dependencies in `requirements.txt` / `package.json`. Do not introduce external services (MySQL/Redis/Docker) without asking first — they are not installed locally.

## Code conventions

Writing or changing code? Read only the matching folder's `AGENTS.md` first, then the single type file your task needs. Rules are mandatory (MUST / MUST NOT) with a one-line rationale and a checklist. Paths are relative to `docs/conventions/`.

- Writing or changing a Vue 3 component, composable, request, store, route or style → `vue3/AGENTS.md`
- Writing or changing a FastAPI router, schema, service, dependency, error or security check → `fastapi/AGENTS.md`
- Touching SQLite schema, migrations, queries, transactions or immutable history → `sqlite/AGENTS.md`
- Writing a comment, docstring, marker or SQL column note → `comments/AGENTS.md`
- Building or adjusting any UI, layout, form or visual style → `ui/AGENTS.md`
