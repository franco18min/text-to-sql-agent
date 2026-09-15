# Archive Report

**Change**: align-portfolio-narrative
**Date**: 2026-09-14
**Mode**: openspec
**Project**: text-to-sql-agent
**Verify verdict**: PASS WITH WARNINGS (no CRITICAL) — safe to archive

## Traceability

Filesystem artifacts (openspec mode; Engram not used):

| Artifact | Path |
|----------|------|
| proposal | `openspec/changes/archive/2026-09-14-align-portfolio-narrative/proposal.md` |
| spec | `.../specs/{recruiter-agent-facts,recruiter-demo-assets,recruiter-eval-narrative}/spec.md` |
| design | `.../design.md` |
| tasks | `.../tasks.md` (13/13 complete) |
| verify-report | `.../verify-report.md` |

## Specs synced

Main `openspec/specs/` had no existing files for these domains. Each change spec is a full capability spec (not ADDED/MODIFIED/REMOVED delta). Copied as-is:

| Domain | Action | Details |
|--------|--------|---------|
| recruiter-agent-facts | Created | 5 requirements copied (EXPLAIN, no zero-row retry, notebook, version 1.0.0, unused schema prompt optional) |
| recruiter-demo-assets | Created | 4 requirements copied (screenshot assets, no invented public demo URL, tests count from pytest, docs-only scope) |
| recruiter-eval-narrative | Created | 2 requirements copied (current headline 100% vs eval JSON; 93.3%/Q16/Q28 as history) |

No destructive REMOVED merges.

## Archive location

`openspec/changes/archive/2026-09-14-align-portfolio-narrative/`

Active `openspec/changes/align-portfolio-narrative/` must not remain after the move.

## Warning carried from verify

Screenshot is Streamlit UI chrome, not a live TPC-H query capture. Specs still require referenced local assets without mocked current 93.3% eval claims.
