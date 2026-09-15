# Skill Registry

Project: text-to-sql-agent
Generated: 2026-09-14
Cache: regenerated
Engram: not updated (MCP down; openspec persistence only)

## Contract

This file is an index. `SKILL.md` at the listed path is the source of truth.
Delegators pass exact paths; they do not summarize skills into compact rules.
Skipped: `sdd-*`, `_shared`, `skill-registry`.
Dedup: skill name unique; project-level wins over user-level; otherwise first scan-order hit.

## Scanned sources

User (existing dirs): `~/.agents/skills`, `~/.kimi/skills`, `~/.config/opencode/skills`, `~/.claude/skills`, `~/.gemini/skills`, `~/.gemini/antigravity/skills`, `~/.cursor/skills`, `~/.qwen/skills`.
User (missing): `~/.pi/agent/skills`, `~/.config/agents/skills`, `~/.config/kilo/skills`, `~/.copilot/skills`, `~/.codex/skills`, `~/.codeium/windsurf/skills`, `~/.kiro/skills`, `~/.openclaw/skills`.
Project: none (`skills/`, `.cursor/skills`, `.atl/skills`, and other listed project skill dirs absent).
Convention files: none (`AGENTS.md`, `CLAUDE.md`, `.cursorrules`, `GEMINI.md`, `copilot-instructions.md` absent).

## Indexed skills (13)

| name | trigger / description | scope | path |
| --- | --- | --- | --- |
| mmx-cli | Use mmx to generate text, images, video, speech, and music via the MiniMax AI platform. Use when the user wants to create media content, chat with MiniMax models, perform web search, or manage MiniMax API resources from the terminal. | user | `C:\Users\magna\.agents\skills\mmx-cli\SKILL.md` |
| kimi-webbridge | Kimi WebBridge lets AI control the user's real browser — navigate, click, type, read, screenshot, and interact with any website using the user's actual login sessions. Use this skill whenever the user wants to interact with websites, automate browser tasks, scrape web content, or perform any action requiring a real browser. Also use when the user mentions "browser", "webpage", "open URL", "screenshot", or asks to read/interact with any website. | user | `C:\Users\magna\.kimi\skills\kimi-webbridge\SKILL.md` |
| branch-pr | Create Gentle AI pull requests with issue-first checks. Trigger: creating, opening, or preparing PRs for review. | user | `C:\Users\magna\.config\opencode\skills\branch-pr\SKILL.md` |
| chained-pr | Trigger: PRs over 400 lines, stacked PRs, review slices. Split oversized changes into chained PRs that protect review focus. | user | `C:\Users\magna\.config\opencode\skills\chained-pr\SKILL.md` |
| cognitive-doc-design | Design docs that reduce cognitive load. Trigger: writing guides, READMEs, RFCs, onboarding, architecture, or review-facing docs. | user | `C:\Users\magna\.config\opencode\skills\cognitive-doc-design\SKILL.md` |
| comment-writer | Write warm, direct collaboration comments. Trigger: PR feedback, issue replies, reviews, Slack messages, or GitHub comments. | user | `C:\Users\magna\.config\opencode\skills\comment-writer\SKILL.md` |
| ecosistema-unified | Ecosistema Gentleman — 3 pilares (context-mode + CodeGraph + Engram). Trigger: cualquier tarea de código, exploración, implementación, análisis estructural, o preguntas sobre el ecosistema. NO usar dentro de fases SDD (seguir sdd-phase-common.md en su lugar). | user | `C:\Users\magna\.config\opencode\skills\ecosistema-unified\SKILL.md` |
| go-testing | Trigger: Go tests, go test coverage, Bubbletea teatest, golden files. Apply focused Go testing patterns. | user | `C:\Users\magna\.config\opencode\skills\go-testing\SKILL.md` |
| issue-creation | Create Gentle AI issues with issue-first checks. Trigger: creating GitHub issues, bug reports, or feature requests. | user | `C:\Users\magna\.config\opencode\skills\issue-creation\SKILL.md` |
| judgment-day | Trigger: judgment day, dual review, adversarial review, juzgar. Run blind dual review, fix confirmed issues, then re-judge. | user | `C:\Users\magna\.config\opencode\skills\judgment-day\SKILL.md` |
| skill-creator | Trigger: new skills, agent instructions, documenting AI usage patterns. Create LLM-first skills with valid frontmatter. | user | `C:\Users\magna\.config\opencode\skills\skill-creator\SKILL.md` |
| skill-improver | Trigger: improve skills, audit skills, refactor skills, skill quality. Audit and upgrade existing LLM-first skills. | user | `C:\Users\magna\.config\opencode\skills\skill-improver\SKILL.md` |
| work-unit-commits | Plan commits as reviewable work units. Trigger: implementation, commit splitting, chained PRs, or keeping tests and docs with code. | user | `C:\Users\magna\.config\opencode\skills\work-unit-commits\SKILL.md` |

## Skipped / duplicates

- Skipped by name: all `sdd-*`, `_shared`, `skill-registry` (opencode, claude, gemini, antigravity, cursor, qwen copies).
- Duplicates (kept first scan-order path): `kimi-webbridge` also in `~/.claude/skills`; Gentleman skills also in `~/.claude`, `~/.gemini`, `~/.gemini/antigravity`, `~/.cursor`, `~/.qwen`.
- Not in init-details scan list (omitted): `~/.cursor/skills-cursor`.
