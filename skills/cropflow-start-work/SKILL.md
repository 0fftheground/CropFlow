---
name: cropflow-start-work
description: Restore CropFlow context at the beginning of a day or fresh session. Use when working in the CropFlow repo and the user asks to start today's work, resume progress, review the active phase, summarize recent completed changes, recover repo state, or decide the next tasks before editing code.
---

# CropFlow Start Work

## Overview

Use this skill at the beginning of a fresh CropFlow session or development day.

Rebuild only the context needed to continue the current phase, summarize recent relevant changes, and recommend what to work on next before any code is modified.

## Core Rules

- Read stable context before broad repo exploration: `AGENTS.md`, `docs/ai/README.md`, `project-context/entrypoints.md`, `project-context/development-plan.md`, `project-context/current-memory.md`, then the current phase document.
- Do not reread the whole `docs/` tree unless the current task requires deeper verification.
- Treat `project-context/current-memory.md` as the current phase snapshot, not as a full backlog.
- If the working tree is dirty, account for in-progress changes before recommending the next task.
- If `current-memory.md` and the repo state disagree, verify the affected files and explain the mismatch.
- Read recent relevant `docs/change-notes/` when they help explain where work stopped or what the next task depends on.
- Do not modify code while using this skill.

## Workflow

### 1. Inspect repo state

Run a minimal repo check:

- `git status --short`
- `git branch --show-current`
- `git log -3 --oneline` when recent commits help explain where work stopped

Use this to determine whether work is already in progress and whether the current branch context matters for the recommendation.

### 2. Read the handoff backbone

Read files in this order:

1. `AGENTS.md`
2. `docs/ai/README.md`
3. `project-context/entrypoints.md`
4. `project-context/development-plan.md`
5. `project-context/current-memory.md`
6. The current phase document named in the plan or memory

Then read recent relevant change notes or decisions only when they affect the active area.

Only read additional `docs/` or code files after identifying the active phase, the current blocker, or the file that the next task will likely touch.

### 3. Reconstruct the current position

Extract and restate:

- current project goal
- current phase
- phase goal
- recent completed changes that still matter
- progress that still matters
- remaining work for the active phase
- blockers or pending decisions
- the next 1 to 3 most likely tasks
- the next docs or code areas to read before each task

Prefer conclusions over restating document structure.

### 4. Recommend the next move

Return a concise start-of-day brief:

- one sentence on the current phase and repo state
- one short note on recent changes that matter today
- one short list of the next 1 to 3 concrete tasks
- one short note on blockers, risks, or decisions that could stall progress

If the user already named a target task, tailor the recommendation to that task instead of giving a generic summary.

## Output Expectations

Return:

- the current project goal
- the current phase
- the active goal
- a concise progress summary
- the recent changes that still matter
- the next recommended tasks
- the key risks or blockers
- the next docs to read before implementation

## CropFlow-Specific Anchors

Use these repository files as the default startup path:

- `AGENTS.md`
- `docs/ai/README.md`
- `project-context/entrypoints.md`
- `project-context/development-plan.md`
- `project-context/current-memory.md`
- `project-context/phases/`
- `docs/wiki-index.md`

Treat `docs/README.md`, `docs/change-notes/`, and the deeper `docs/` tree as follow-up sources selected by the active area, not default full-tree reads.

## Example Requests

- `Start today's work`
- `Restore the current CropFlow progress`
- `Review the active phase and tell me what to do next`
- `Read current-memory and suggest the next P1 task`
- `Summarize recent CropFlow changes and tell me what to work on today`
