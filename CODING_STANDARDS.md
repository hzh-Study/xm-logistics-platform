# Coding standards (review-time)

Read during code review. The mandatory MUST/MUST-NOT rules live in the convention files pointed to by `AGENTS.md` (fastapi, sqlite, vue3, ui, comments) and in `GLOSSARY.md` + `docs/adr/`; this file holds only the cross-file judgement calls a linter cannot express. Mechanical rules (version-block order, `SELECT *`, `utcnow`) are enforced by `backend/tests/test_migration_integrity.py` — do not restate them here.

## Judgement calls

- **Append-only current view.** The live record is the one with `replaced_by IS NULL`; superseded rows keep a forward `replaced_by` pointer to their replacement. A `MAX(id)` "current" view or a backward pointer on the new row is wrong, even where the history table makes it convenient. See `docs/conventions/sqlite/append-only-history.md`, ADR-0004.
- **Status and decision literals come from `GLOSSARY.md` verbatim.** e.g. 认证状态 is `审核通过`/`审核不通过`; a legacy DB CHECK using different literals is tolerated only when an additive migration cannot rewrite it, and is then translated through a single helper — never duplicated switches across services. See ADR-0003.
- **Admin is read-only on business records.** Admin may append exception/history records and change master-data ownership with an appended audit trail; it must not rewrite orders, tasks, check-ins or expenses. See ADR-0004.
- **State dimensions stay orthogonal.** Availability, employment and account status are independent fields; one transition must not silently derive another unless a spec line says so. See ADR-0003.
- **Snapshots are frozen at publish.** Copy shipping/receiving data into the order at publish time; later warehouse or coordinate edits must never rewrite an existing order's snapshot. See ADR-0001, ADR-0008.
- **Submit entries own their form state.** When one page has multiple submit paths (login / register / per-role register), each keeps its own form refs. Never reuse another path's `v-model` fields — a prefilled login identity leaking into a register handler makes registration fail on an already-taken phone. See `docs/conventions/vue3/component.md`.
