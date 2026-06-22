---
name: cropflow-wiki-maintenance
description: Audit and maintain the CropFlow project wiki. Use when docs may be stale, duplicated, weakly linked, missing recent behavior, missing decisions or change-notes, or drifting away from the current code and workflow model. Best for periodic cleanup, post-phase review, or after several tasks land.
---

# CropFlow Wiki Maintenance

## Overview

Use this skill periodically to keep CropFlow docs accurate, navigable, and aligned with the implemented system.

Audit first, then make low-risk fixes directly and propose higher-risk cleanup before deleting or reshaping historical material.

## Core Rules

- Treat the wiki as long-term project memory, not as a copy of chat history.
- Prefer improving existing docs over creating many new pages.
- Fix obvious stale links, missing index entries, and directory drift directly.
- Do not delete historical docs or merge away evidence-bearing material without user confirmation.
- When docs and code disagree, verify the relevant source files before declaring drift.

## Workflow

### 1. Read the doc backbone

Start with:

1. `AGENTS.md`
2. `docs/ai/README.md`
3. `docs/README.md`
4. `docs/wiki-index.md`
5. `project-context/entrypoints.md`
6. `project-context/current-memory.md`

Then read only the area docs relevant to the maintenance pass.

### 2. Audit for drift and gaps

Check for:

- docs that no longer match code or current workflow
- missing docs for implemented behavior
- missing change-notes for important completed work
- missing decisions for long-term frozen rules
- outdated paths or broken links
- duplicated or overlapping pages
- docs in the wrong directory layer

### 3. Make low-risk fixes

Directly fix:

- stale path references
- index omissions
- obvious wording mismatches
- lightweight navigation problems

Do not delete or heavily merge documents in this step.

### 4. Propose higher-risk cleanup

For deletions, merges, or history reshaping, return a short cleanup plan first.

Make the plan explicit about:

- which docs overlap
- what would become the new fact source
- what should stay in `docs/history/`
- what should move to `docs/change-notes/` or `docs/decisions/`

### 5. Return a maintenance report

Return:

- docs reviewed
- direct fixes made
- remaining drift
- missing docs or records
- higher-risk cleanup proposals

## Output Expectations

Return:

- documents reviewed
- direct fixes made
- stale or duplicated areas
- missing docs, ADRs, or change-notes
- broken links or index gaps
- recommended cleanup plan
- items requiring user confirmation

## CropFlow-Specific Anchors

Prefer these repository files during maintenance:

- `docs/wiki-index.md`
- `docs/README.md`
- `docs/decisions/`
- `docs/change-notes/`
- `docs/domain/`
- `docs/workflow/`
- `docs/history/`
- `docs/maintenance/docs-hygiene-plan.md`

## Example Requests

- `Use $cropflow-wiki-maintenance to audit the current docs for drift`
- `Check whether recent workflow changes are missing from the wiki`
- `Review the wiki after this phase and suggest cleanup`
