@AGENTS.md

## Claude Code notes for the FreshyFresh Command Center (Rayfin `dataapp` template)
- **Instructions load order.** `AGENTS.md` (imported above) comes from the `dataapp` template and is authoritative
  for this app's read path. The repo-root `CLAUDE.md` also loads; its accuracy and Fabric-safety rules apply.
- **Skills.** Claude Code does not auto-discover `.agents/skills/`. Read the relevant `SKILL.md` before each kind
  of work:
  - schema / DAX: `schema-discovery`, `query-design`, `dax-authoring`
  - visuals and layout: `visuals`, `app-design`
  - validation: `app-validation`, `playwright-cli`
  - connections: `fabric-cli`, `fabric-sdk`
  - Rayfin backend (writeback): `rayfin`, `rayfin-functions`, `rayfin-connectors`
- **Read path.**
  - Microsoft's `fabric-app-data` SDK queries `SM_FreshyFresh_Ops` (connection alias `ambermoor`, registered with
    `npx fabric-app-data add ambermoor --from-url "<model URL>"`).
  - The app runs embedded in the Fabric portal as the signed-in user, so model RLS applies.
  - Discover the schema with `npx fabric-app-data query` (INFO.VIEW.*). Don't guess column names.
- **Write path.**
  - Rayfin entities for QualityHold / CorrectiveAction / HoldUpdate.
  - The template ships with `services.data.enabled: false`. Enable it with `dialect: mssql`, following
    `https://rayfin.ai/docs/data/modeling.md` and `https://rayfin.ai/docs/reference/agent-rules.md`.
- **Dev loop (this template).**
  - `npm run dev` runs Vite. Open the app item in Fabric with `&devUri=http://localhost:5173`.
  - Validate with `npm run validate:visual` and the portal embed flow. Never test against bare localhost.
- **Deploy.** `npx rayfin up --workspace-uri "<WS-FRESHYFRESH-APP URL>"`, then `npx rayfin up status`.
  Ask Shekhar first. Never `--force`.
- **Spec.** `../docs/specs/app-command-center.md`. Golden numbers: `../agent/golden_answers.json`.
