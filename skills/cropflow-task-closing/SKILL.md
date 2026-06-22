---
name: cropflow-task-closing
description: Close one completed CropFlow feature, bug fix, refactor, or business logic change. Use when a single task scope is done and you need to review the final diff, summarize behavior changes, run or report tests, update affected docs, add decisions or change-notes when needed, and prepare a reviewable close-out before commit.
---

# CropFlow Task Closing

## Overview

Use this skill after one concrete CropFlow task is complete.

Close the task at the knowledge level, not just the code level: verify scope, update docs by impact area, record tests, and produce a reviewable summary before commit or handoff.

## Core Rules

- Scope this skill to one completed task, not a whole day of mixed work.
- Inspect the actual diff before writing summaries or docs.
- Update only the docs affected by the completed task.
- If the working tree mixes multiple scopes and the task boundary is unclear, stop and ask before writing broad close-out notes.
- Do not treat `project-context/current-memory.md` as the main long-term record; use `docs/change-notes/` and `docs/decisions/` when appropriate.

## Workflow

### 1. Confirm the task scope

Start with:

- `git status --short`
- `git diff --stat`

Then inspect only the files relevant to the completed task.

Separate:

- files belonging to the completed task
- unrelated edits
- unfinished work that should not be summarized as complete

### 2. Summarize the task outcome

Identify:

- what changed in code
- what changed in business behavior
- affected domain objects
- affected workflows
- affected APIs, pages, jobs, or tables
- compatibility or migration concerns

Keep the summary centered on behavior and impact, not file inventory.

### 3. Verify tests and validation

Run relevant tests when practical.

Report:

- passed tests
- failed tests
- tests not run and why
- manual verification steps still needed

### 4. Update project knowledge

Update only the docs that this task changed:

- `docs/model/` for object, field, and state changes
- `docs/architecture/` for module or boundary changes
- `docs/workflow/` for workflow, job, or event changes
- `docs/api/` for request, response, or field contract changes
- `docs/domain/` for long-term direction knowledge changes
- `docs/frontend/` for page, display, and handoff changes
- `docs/decisions/` when the task freezes a long-term design choice
- `docs/change-notes/` when the task is complete and worth future review

Update `project-context/current-memory.md` only if the completed task changes current phase progress, next step, blocker state, or still-relevant assumptions.

### 5. Produce a close-out summary

Return:

- code changes
- business logic changes
- affected areas
- tests
- docs updated
- remaining assumptions
- manual review checklist
- suggested commit message

Do not commit unless the user asks.

## Output Expectations

Return:

- concise task summary
- affected areas
- test results
- doc updates
- ADR updates if any
- change-note created or updated
- current-memory update status
- manual review checklist
- suggested commit message

## CropFlow-Specific Anchors

Use these repository files as the task-closing backbone:

- `docs/wiki-index.md`
- `docs/change-notes/`
- `docs/decisions/`
- `project-context/current-memory.md`

If the task changed long-term behavior, prefer updating formal docs first and only then writing the change-note.

## Example Requests

- `Use $cropflow-task-closing to close this disease-pest review task`
- `Summarize this completed backend change and update docs before commit`
- `Close this refactor with tests, ADR check, and change-note`
