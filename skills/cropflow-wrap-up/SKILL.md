---
name: cropflow-wrap-up
description: Wrap up one CropFlow work day or session by inspecting changed files, refreshing handoff memory, summarizing what was completed today, and preparing git actions when requested. Use at end of day or end of session, not as the main close-out step for every single task.
---

# CropFlow Wrap Up

## Overview

Use this skill at the end of a CropFlow work day or handoff session.

Compress the day into a stable next-session handoff, refresh `current-memory`, and prepare git actions only for the scope the user wants to submit.

## Core Rules

- Inspect actual git change scope before writing memory or proposing a commit.
- Treat `project-context/current-memory.md` as the single source for current phase status.
- Keep memory short. Write conclusions, current status, blockers, and next step. Do not keep long reasoning or completed discussion that no longer affects follow-up work.
- Keep full backlog and phase scope in `project-context/development-plan.md` and `project-context/phases/`.
- Do not stage or commit unrelated user changes. If the working tree mixes multiple scopes and the intended commit boundary is unclear, stop and ask.
- Do not use this skill as a replacement for per-task closing.
- If a completed task still needs tests, ADR updates, or a change-note, first identify that gap explicitly.
- If the missing close-out scope is clear and small, complete it inside wrap-up before finishing the day-end handoff.
- If task boundaries are mixed or the missing close-out is too broad, call that out and recommend a dedicated task-closing pass.

## Workflow

### 1. Inspect actual change scope

Start with:

- `git status --short`
- `git diff --stat`
- optionally `git log -3 --oneline` when today’s recent commits help explain the handoff

Then inspect only the changed files needed to understand the completed work:

- use targeted `git diff -- <path>` for tracked changes
- read newly added files directly when needed

Separate:

- changes completed today
- completed task scopes that are ready for task-level close-out
- unrelated pre-existing edits
- incomplete work that should remain unstaged

### 2. Refresh the handoff memory

Update `project-context/current-memory.md` based on the actual repo state and the active phase.

Update only these sections as needed:

- `Current Phase`
- `Phase Goal`
- `Progress`
- `Remaining`
- `Blockers`
- `Next Step`
- `Last Updated`

Rules:

- keep it short
- keep only still-relevant conclusions
- do not copy the full backlog
- do not list document entrypoints here
- if phase scope or acceptance criteria changed, update the phase document or `development-plan.md` as well instead of forcing everything into memory
- if today completed an important task that should have a change-note or decision record, add it before finishing when the scope is clear; otherwise record the gap explicitly in the wrap-up output

### 3. Summarize today’s handoff

Return a short day-end summary that makes the next session fast to resume:

- what was completed today
- what remains in progress
- what should be picked up first next time
- any doc or verification gaps still open
- whether any task-level close-out was completed inside wrap-up versus deferred

### 4. Optionally write a short session log

If a dated trace would help future handoff clarity, append a short note to `project-context/session-log/YYYY-MM-DD.md`.

Keep the log lightweight:

- what changed today
- what remains open
- what the next session should pick up first

Do not require a session log for every run.

### 5. Prepare a commit message

Draft the commit message from the dominant completed scope, not from a file inventory.

Use an imperative message such as:

- `docs: align CropFlow handoff memory with P1 contract state`
- `planning: refine P1 handoff and phase mapping`
- `feat: finalize weed-control closed-loop data model drafts`

If the user asked only for a summary, propose the commit message without committing.

### 6. Commit safely when requested

If the user asked to commit:

- stage only the files that match the agreed work scope
- use non-interactive git commands
- commit only after confirming the staged set is coherent

If unrelated changes are mixed into the working tree and cannot be cleanly separated with confidence, stop and ask before creating a broad commit.

### 7. Push when requested

If the user asked to push:

- push the current branch
- if no upstream exists, set upstream explicitly
- report the branch name and push result

Do not invent a branch strategy unless the user asked for it.

## Output Expectations

Return:

- what changed today
- which completed tasks are fully closed versus only partially handed off
- how `current-memory.md` was updated
- the proposed or actual commit message
- whether commit and push were completed
- any work intentionally left for the next session
- any missing doc, test, or verification follow-up

## CropFlow-Specific Anchors

Use these repository files as the default wrap-up path:

- `project-context/current-memory.md`
- `project-context/development-plan.md`
- `project-context/phases/`
- `project-context/session-log/`
- `docs/change-notes/`

Read deeper `docs/` files only when the changed scope or a blocker needs verification.

## Example Requests

- `Wrap up today's work`
- `Summarize progress and update current-memory`
- `Prepare a commit message for today's CropFlow changes`
- `Commit this work item and push the branch`
- `Finish today's handoff and tell me what the next session should start with`
