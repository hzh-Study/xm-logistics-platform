## Agent skills

### Issue tracker

Issues live in this repo's GitHub Issues (`hzh-Study/xm-logistics-platform`), managed with the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

The five canonical triage roles are used verbatim as label strings. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one root `GLOSSARY.md` plus `docs/adr/`. See `docs/agents/domain.md`.

## Code conventions

Writing or changing code? Read only the matching folder's `AGENTS.md` first, then the single type file your task needs. Rules are mandatory (MUST / MUST NOT) with a one-line rationale and a checklist. Paths are relative to `docs/conventions/`.

- Writing or changing a Vue 3 component, composable, request, store, route or style → `vue3/AGENTS.md`
- Writing or changing a FastAPI router, schema, service, dependency, error or security check → `fastapi/AGENTS.md`
- Touching SQLite schema, migrations, queries, transactions or immutable history → `sqlite/AGENTS.md`
- Writing a comment, docstring, marker or SQL column note → `comments/AGENTS.md`
- Building or adjusting any UI, layout, form or visual style → `ui/AGENTS.md`
