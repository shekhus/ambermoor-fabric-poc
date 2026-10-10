---
name: rayfin-app
description: Build, run or deploy the Ambermoor Freshness Command Center Fabric App (Rayfin dataapp template) - scaffolding, semantic-model visuals via fabric-app-data, hold/corrective-action writeback via Rayfin entities, RLS testing, rayfin up. Use for any work under app/ or questions about Fabric Apps / Rayfin.
---

# Fabric App (Rayfin `dataapp` template): working rules

**Status.**
- Fabric Apps is **Preview**.
- Rayfin's own service status (GA/Experimental) is in `https://rayfin.ai/docs/reference/changelog.md`.
- The `dataapp` template repo says it is "under active development". Re-check its README after scaffolding.

## Where to run
- **Scaffolding (step 0):** repo root.
- **Everything else:** `app/`.
  - If the working directory isn't `app/`, stop and ask Shekhar to restart Claude Code there.
  - Reason: the `rayfin` MCP and the template's `AGENTS.md` / `.agents/skills/` live there.

## Step 0: scaffold (with Shekhar's OK)
```bash
npx rayfin init --list-templates            # confirm the "dataapp" name in the installed CLI
npm create @microsoft/rayfin@latest app -- --template dataapp
cp templates/app-CLAUDE.md app/CLAUDE.md
cd app && npm install
```
- Commit `app/rayfin/.lockfile.json`.
- Never commit `app/rayfin/.env`, `app/rayfin/.deployments.json`, `.env.local` or `.env.fabric`.

## Read before coding (Claude Code doesn't auto-load these)
- `app/AGENTS.md`: the template's rules. Its read-path rules win for this app:
  - no mock data;
  - discover the schema with `INFO.VIEW.*`;
  - query-factory pattern;
  - visual validation.
- `app/.agents/skills/`. Read the ones relevant to the task:
  - schema and DAX: `schema-discovery`, `query-design`, `dax-authoring`
  - presentation: `visuals`, `app-design`
  - validation: `app-validation`, `playwright-cli`
  - connections: `fabric-cli`, `fabric-sdk`
  - Rayfin backend: `rayfin`, `rayfin-functions`, `rayfin-connectors`
- `https://rayfin.ai/docs/reference/agent-rules.md` and `known-limitations.md` before touching entities
  (writeback).
- `../docs/specs/app-command-center.md` (the spec) and `../agent/golden_answers.json`.

## Workflow
1. `npx rayfin login`. Then `npx rayfin up --workspace-uri "<WS-AMBERMOOR-APP URL>"` provisions the item.
   Ask first.
2. `npx fabric-app-data add ambermoor --from-url "<SM_Ambermoor_Ops URL>"`. Then probe the schema with
   `npx fabric-app-data query`.
3. Build page by page. Validate each visual with `npm run validate:visual` before UI work.
4. Preview with `npm run dev`, then open the app item in Fabric with `&devUri=http://localhost:5173`.
5. **Writeback.** Enable `services.data` (`dialect: mssql`). Add entities with explicit permission decorators and
   `@text({ max })`. Restart the dev loop. Then run `npx rayfin up` → `npx rayfin up status`.
6. Never `--force`. Never deploy to a workspace other than `WS-AMBERMOOR-APP` without explicit instruction.

## Non-negotiables
- KPI tiles must match `agent/golden_answers.json` (spec acceptance tests).
- Test RLS as `qa.p03`. That user has Read + Build on the model and is NOT Contributor+ on `WS-AMBERMOOR-DEV`,
  because those roles bypass RLS. The deployer's own view proves nothing.
- Every entity has an explicit permission decorator. No silent `authenticated: *`.
