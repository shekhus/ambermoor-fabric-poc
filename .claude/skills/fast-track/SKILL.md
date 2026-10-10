---
name: fast-track
description: Drive the weekend fast track that gets the Ambermoor Fabric App and the "Ask Ambermoor" agent working (FT0-FT6) - prep, data load, Eventhouse, semantic model, Claude Code agent, Fabric App, Fabric Data Agent on F2. Use when Shekhar says "fast track", "next step", "FT<n>", or asks how to get the app/agent running.
argument-hint: "[FT0..FT6 | next | status]"
---

# Fast track runner

Request: $ARGUMENTS. With `next` or empty, take the first unticked FT step in `docs/phase-plan.md`.
With `status`, report what's ticked, what's blocked and why.

## Procedure
1. **Prepare.**
   - Read the step in `docs/fast-track.md`. For FT3 also read `fabric/semantic-model/SM_Ambermoor_Ops.md`.
     For FT4 also read `docs/specs/app-command-center.md`.
   - Check prerequisites from earlier steps. If one is missing, say so and stop.
2. **Split the work into 🤖 and 🖱️.**
   - 🤖 Do the parts you can from here: local commands, `fabric_query.py` reads, file edits.
   - 🖱️ For portal-only parts, give a numbered click-path and wait for Shekhar to confirm.
   - Ask before any Fabric write: `fabric` MCP create/upload, `rayfin up`, notebook runs on his capacity.
3. **Verify** every Fabric feature you rely on with the `microsoft-learn` MCP. State **GA / Preview / unverified**.
   If the portal differs from the runbook (labels change monthly), trust the portal, then update `docs/fast-track.md`.
4. **Check acceptance.**
   - Run the step's ✅ check and compare with `agent/golden_answers.json`.
   - Never mark a step done on a partial pass. Record the gap in `docs/lab-log.md` and propose the fix.
5. **Close out.**
   - Tick the step in `docs/phase-plan.md`.
   - Add a short `docs/lab-log.md` entry: what, gotcha, DP-700 tag if any, Learn link.
   - Name the next step.

## Step-specific rules
- **FT1/FT2**: the notebooks and KQL are tested locally. If Fabric output differs, suspect environment first:
  default lakehouse not attached, schemas not enabled, session time zone.
- **FT3**: the DAX hasn't been executed in a model yet. Run validation queries A–D before any app work.
- **FT4**:
  - Must run from `app/` (the `rayfin` MCP and the template's AGENTS.md live there).
  - If you're at the repo root, finish steps 1–3, then tell Shekhar to restart Claude Code in `app/`.
- **FT5**: execute via `tools/fabric_query.py` (read-only). If `fabric.endpoints.json` is missing, ask for the
  SQL endpoint host and KQL Query URI.
- **FT6**:
  - Remind Shekhar about cost and pausing the F2.
  - If the agent can't read trial-workspace sources, apply fallback a, then b, from the runbook.
