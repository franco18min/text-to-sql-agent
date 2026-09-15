# Archive Report

**Change**: harden-packaging
**Date**: 2026-09-14
**Mode**: openspec
**Project**: text-to-sql-agent
**Verify verdict**: PASS WITH WARNINGS (no CRITICAL) — safe to archive

## Traceability

Filesystem artifacts (Engram unavailable — `user-engram` MCP discovery failed; observation IDs N/A):

| Artifact | Path |
|----------|------|
| proposal | `openspec/changes/archive/2026-09-14-harden-packaging/proposal.md` |
| spec | `.../specs/{ci-editable-install,docker-env-example,eval-set-shipping,gemini-default-model,unified-version,windows-pytest-docs}/spec.md` |
| design | `.../design.md` |
| tasks | `.../tasks.md` (15/15 complete) |
| verify-report | `.../verify-report.md` |

## Specs synced

Main `openspec/specs/` had no existing files for these domains. Each change spec is a full capability spec (not ADDED/MODIFIED/REMOVED delta). Copied as-is:

| Domain | Action | Details |
|--------|--------|---------|
| ci-editable-install | Created | 1 requirement copied (editable install with dev extras) |
| docker-env-example | Created | 1 requirement copied (copy real env example filename) |
| eval-set-shipping | Created | 1 requirement copied (track eval set; ignore results) |
| gemini-default-model | Created | 1 requirement copied (default without .env) |
| unified-version | Created | 1 requirement copied (version 1.0.0 everywhere) |
| windows-pytest-docs | Created | 1 requirement copied (Windows pytest without Make) |

No destructive REMOVED merges.

## Archive location

`openspec/changes/archive/2026-09-14-harden-packaging/`

Active `openspec/changes/harden-packaging/` must not remain after the move.
