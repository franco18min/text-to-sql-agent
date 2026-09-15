# Archive Report

**Change**: fix-schema-surface
**Date**: 2026-09-14
**Mode**: openspec
**Project**: text-to-sql-agent
**Verify verdict**: PASS WITH WARNINGS (no CRITICAL) — safe to archive

## Traceability

Filesystem artifacts (Engram unavailable — `user-engram` MCP discovery failed; observation IDs N/A):

| Artifact | Path |
|----------|------|
| proposal | `openspec/changes/archive/2026-09-14-fix-schema-surface/proposal.md` |
| spec | `.../specs/{api-cors-origins,schema-demo-notebook,schema-http-api}/spec.md` |
| design | `.../design.md` |
| tasks | `.../tasks.md` (13/13 complete) |
| verify-report | `.../verify-report.md` |

## Specs synced

Main `openspec/specs/` had no existing files for these domains. Each change spec is a full capability spec (not ADDED/MODIFIED/REMOVED delta). Copied as-is:

| Domain | Action | Details |
|--------|--------|---------|
| api-cors-origins | Created | 2 requirements copied (subdomain origins, local Streamlit exact) |
| schema-demo-notebook | Created | 2 requirements copied (listing, column types) |
| schema-http-api | Created | 4 requirements copied (catalog listing, HTTP keys, Streamlit keys, API tests) |

No destructive REMOVED merges.

## Archive location

`openspec/changes/archive/2026-09-14-fix-schema-surface/`

Active `openspec/changes/fix-schema-surface/` must not remain after the move.
