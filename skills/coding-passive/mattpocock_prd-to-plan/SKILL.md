---
name: prd-to-plans
description: Break a plan, spec, or PRD into independently-grabbable implementation plans using tracer-bullet vertical slices. Use when user wants to convert a PRD or idea into implementation plans and break down the work into milestones.
---

# PRD to plan

Break a plan into independently-grabbable plans using vertical slices (tracer bullets).

plans are saved in `.agents/plans/prd-XXXX-plan-YY`. replace `XXXX` with the PRD number and `YY` with the plan number.

## Process

### 1. Gather context

Work from whatever is already in the conversation context. If the user passes an prd reference (PRD  number, URL, or path) as an argument, read its full body and comments.

### 2. Explore the codebase (optional)

If you have not already explored the codebase, do so to understand the current state of the code. plan titles and descriptions should use the project's domain glossary vocabulary, and respect ADRs in the area you're touching.

### 3. Draft vertical slices

Break the plan into **tracer bullet** plans. Each issue is a thin vertical slice that cuts through ALL integration layers end-to-end, NOT a horizontal slice of one layer.

Slices may be 'HITL' or 'AFK'. HITL slices require human interaction, such as an architectural decision or a design review. AFK slices can be implemented and merged without human interaction. Prefer AFK over HITL where possible.

<vertical-slice-rules>
- Each slice delivers a narrow but COMPLETE path through every layer (schema, API, UI, tests)
- A completed slice is demoable or verifiable on its own
- Prefer many thin slices over few thick ones
</vertical-slice-rules>

### 4. Quiz the user

Present the proposed breakdown as a numbered list. For each slice, show:

- **Title**: short descriptive name
- **Type**: HITL / AFK
- **Blocked by**: which other slices (if any) must complete first
- **User stories covered**: which user stories this addresses (if the source material has them)

Ask the user:

- Does the granularity feel right? (too coarse / too fine)
- Are the dependency relationships correct?
- Should any slices be merged or split further?
- Are the correct slices marked as HITL and AFK?

Iterate until the user approves the breakdown.

