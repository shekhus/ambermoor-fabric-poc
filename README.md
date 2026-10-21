# FreshyFresh Ops: Microsoft Fabric POC (Claude Code starter kit)

One project that combines two reference demos:
- **Fabric App + Rayfin** (from "Build Your First Microsoft Fabric App with AI"): app with a semantic-model read,
  writeback and RLS.
- **Fabric Data Agent** (from "From Data to Insights with Microsoft Fabric Data Agents"): natural language over a
  lakehouse, a model and an eventhouse.

The storyline is **FreshyFresh Foods**, a *fictional* refrigerated prepared-foods company. All data is
synthetic, and no real company is represented.

**Order of work:** a weekend **fast track** gets the Fabric App and the "Ask FreshyFresh" agent running
(`docs/fast-track.md`, `/fast-track`). DP-700 labs follow (`docs/phase-plan.md`, `/dp700-lab`).

## Start in 10 minutes
1. Unzip, `git init`, open the folder in VS Code.
2. `python -m venv .venv`, activate it, then `pip install -r requirements.txt`.
3. Generate and check the data:
   ```bash
   python tools/generate_freshyfresh_data.py --out data/generated --seed 42
   python tools/verify_golden.py --data data/generated
   ```
   Expect 9× PASS.
4. Run `az login --tenant <TENANT_ID> --allow-no-subscriptions`.
5. Start **Claude Code in this folder**. It loads `CLAUDE.md` automatically (no export needed). Approve the
   `fabric` and `microsoft-learn` MCP servers from `.mcp.json`.
6. Check the setup:
   - `/context`: CLAUDE.md is listed.
   - `/skills`: `fast-track`, `dp700-lab`, `freshyfresh-data`, `ask-freshyfresh`, `rayfin-app`.
   - `claude mcp list`: both servers connected.
7. First prompts:
   - `/fast-track status`, then `/fast-track next`

## What's inside
| Path | What |
|---|---|
| `CLAUDE.md` | Project brain: mission, accuracy rules, environment, safety rules, conventions, Databricks→Fabric map |
| `.mcp.json` | `fabric` (local Fabric MCP) + `microsoft-learn` (Learn docs, for verification) |
| `.claude/skills/` | `fast-track` (weekend runner), `dp700-lab` (lab runner + exam drill), `freshyfresh-data`, `ask-freshyfresh` (agent + eval), `rayfin-app` |
| `.claude/settings.json` | Deny rules: no reading `.env`, no `rayfin up --force`, no force-push |
| `tools/` | Data generator, DuckDB golden-answer verifier, **read-only Fabric SQL/KQL query tool**, local notebook runner, Eventstream simulator, Fabric token `headersHelper` |
| `fabric/` | Bronze + fast-track gold notebooks (tested in Spark), semantic model spec (DAX + RLS), KQL cold-chain queries, Warehouse RLS/CLS/DDM reference |
| `agent/` | Ask FreshyFresh instructions + few-shot JSON (Fabric Data Agent import format) + golden answers |
| `docs/` | **fast-track runbook**, setup, architecture, phase plan, data contract, lab log, app spec, agent spec |
| `templates/app-CLAUDE.md` | Becomes `app/CLAUDE.md` after scaffolding the Rayfin app (imports Rayfin's `AGENTS.md`) |

## Key constraints (as verified on 9 Oct 2026; re-check on Learn)
- **Fabric Data Agents don't run on trial capacity** (paid F2+ or P1+). FT6 uses a pay-as-you-go F2 in the
  same region as your trial. FT5 runs Ask FreshyFresh in Claude Code on trial via `tools/fabric_query.py`.
- **Fabric Apps is Preview.** It needs the tenant setting *Fabric Apps (preview)*. It works on trial in
  supported regions.
- Claude Code doesn't read Rayfin's `.agents/skills/`. The `rayfin-app` skill and `app/CLAUDE.md` bridge that.
