---
name: cropflow-task-planning
description: Analyze a non-trivial CropFlow feature, bug fix, refactor, or business logic change before editing code. Use when the task may affect domain objects, workflows, APIs, jobs, tests, or project docs and you need a reviewable implementation plan, impact scope, options, and validation approach first.
---

# CropFlow Task Planning

## Overview

Use this skill before changing code for any non-trivial CropFlow task.

Rebuild only the context needed for the requested change, identify impact scope, compare implementation choices when needed, and stop at a reviewable plan before editing code.

## Core Rules

- Read stable handoff docs before reading broad code or docs trees.
- Do not modify code while using this skill.
- Treat `project-context/current-memory.md` as the current phase snapshot, not as a full backlog.
- Read only the domain, workflow, API, decision, and change-note docs needed for the current task.
- If docs and code disagree, verify the affected source files and state the mismatch explicitly.

## Workflow

### 1. Restore the minimum planning context

Read in this order:

1. `AGENTS.md`
2. `docs/ai/README.md`
3. `project-context/entrypoints.md`
4. `project-context/development-plan.md`
5. `project-context/current-memory.md`
6. The active phase document

Then read only the task-relevant files under:

- `docs/architecture/`
- `docs/model/`
- `docs/workflow/`
- `docs/api/`
- `docs/domain/`
- `docs/frontend/`
- `docs/decisions/`
- `docs/change-notes/`

### 2. Inspect the current implementation

Use targeted code and doc reads to identify:

- current workflow
- involved domain objects
- related services, handlers, jobs, routes, pages, and tables
- current business rules and assumptions
- existing tests and validation path

Do not broaden into unrelated modules.

### 3. Map the requested change

Extract and restate:

- the requested outcome
- affected domain objects
- affected workflows and jobs
- backend impact
- frontend impact
- API impact
- database or migration impact
- historical data or compatibility risk
- docs that must be updated if the change lands

### 4. Compare implementation choices when useful

If the task has meaningful tradeoffs, propose 2 to 3 options.

For each option, keep it short and explain:

- what changes
- why it works
- main risk or cost

If the task is straightforward, say so and recommend the direct path without inventing fake options.

### 5. Produce the execution plan

Return a plan that includes:

- files or modules likely to change
- what to change in each area
- testing plan
- manual verification points
- required doc updates
- open assumptions or business questions

End by waiting for confirmation instead of editing code.

## Output Expectations

Return:

- current understanding
- related docs read
- affected objects and workflows
- impact scope
- implementation options when needed
- recommended plan
- testing plan
- required doc updates
- remaining assumptions or questions

## CropFlow-Specific Anchors

Prefer these repository files as the planning backbone:

- `AGENTS.md`
- `docs/ai/README.md`
- `project-context/entrypoints.md`
- `project-context/development-plan.md`
- `project-context/current-memory.md`
- `project-context/phases/`
- `docs/wiki-index.md`

Read `docs/change-notes/` for recently completed work that may influence the new task.

## Example Requests

- `Use $cropflow-task-planning to assess this new fertilization workflow before coding`
- `Plan the impact of changing disease-pest review behavior`
- `Analyze this refactor and tell me which docs and tests must change`
