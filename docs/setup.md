# Setup reference

The weekend order of work is in `docs/fast-track.md`. This page is the reference behind it.

Status labels follow what I could verify on 9 Oct 2026. Fabric moves fast, so re-check anything marked *verify*.

## 1. What runs on your Fabric **trial** vs what needs **paid F2+**
| Capability | Trial | Source / note |
|---|---|---|
| Lakehouse, Warehouse, notebooks, pipelines, Dataflow Gen2, Eventstream/Eventhouse, Direct Lake, Git, deployment pipelines | ✅ (DP-700 labs) | standard trial scope; *verify* any feature you find greyed out |
| **Fabric Apps (Rayfin)**, Preview | ✅ | Rayfin 1.36 can "start or reuse an eligible Fabric trial capacity"; tenant setting *Fabric Apps (preview)* required; Functions/Storage not in every region (rayfin.ai/docs/deploy/fabric-apps) |
| **Fabric Data Agent** + its MCP endpoint | ❌ | Learn prereq: paid F2+ or P1+. Community threads confirm trial is blocked (learn.microsoft.com/fabric/data-science/data-agent-mcp-server) |
| Copilot-dependent features (e.g. Eventhouse MCP schema discovery) | ❌ likely | *verify*. The Eventhouse remote MCP needs Copilot for schema fetch |

**Plan:** do everything on trial, and add a **pay-as-you-go F2** in Azure only for the Data Agent (FT6).
Assign it only to `WS-AMBERMOOR-AGENT` and **pause it when idle**.

**Create the F2 (Azure portal, same Entra tenant as Fabric):**
1. Create a resource → **Microsoft Fabric** (capacity).
2. Fill in:
   - Subscription and resource group
   - Name, e.g. `ambermoorf2`
   - **Region = your trial capacity's region**. Find it under Admin portal → Capacity settings → Trial.
   - Size **F2**
   - Capacity administrator: you
3. Once it's active, go to Fabric → `WS-AMBERMOOR-AGENT` → Workspace settings → Workspace type (formerly "License info") → assign the F2.
4. Pause and resume from the capacity's Overview page in Azure. Pausing stops compute billing. Check
   storage/OneLake billing separately on Learn.

**Cost (approximate):**
- One third-party source quotes about **$0.36/hour (≈ $0.18 per CU-hour), ~$263/month if never paused**, for
  US West 2 from the July 2026 Azure retail list.
- Your region and currency will differ. Verify in the Azure pricing calculator.
- Data agents also consume CUs, so F2 may throttle under heavy testing.

## 2. Tenant settings (Fabric admin portal → Tenant settings)
| Setting | Needed for | Step |
|---|---|---|
| Users can create Fabric items | everything | FT0 |
| **Fabric Apps (preview)** | Rayfin app | FT4 |
| Semantic model "Dataset Execute Queries REST API" (exact label: *verify*) | app reads the model | FT4 |
| XMLA endpoint (Read or Read Write) | data agent over a semantic model | FT6 |
| **Fabric data agent** | data agent | FT6 |
| Copilot and Azure OpenAI Service features | data agent | FT6 |
| Cross-geo processing / storing for AI (if your capacity region requires it) | data agent + its MCP | FT6 |

## 3. Workspaces and identities
1. Start the Fabric trial if it isn't active (Account manager → Start trial). Note the capacity region.
2. Create `WS-AMBERMOOR-DEV`, `WS-AMBERMOOR-TEST` and `WS-AMBERMOOR-APP`. Workspace settings → Workspace type (formerly "License info") → Fabric Trial + capacity.
3. Create **two test users** in your Entra tenant, for example `qa.p03@…` and `ops.director@…`. RLS must be
   tested with users who are **not** workspace Contributor/Member/Admin, because those roles bypass RLS.
4. Put IDs in `CLAUDE.local.md` (gitignored), for example:
   ```
   TENANT_ID=…  WS_DEV_ID=…  LH_AMBERMOOR_ID=…  WS_APP_ID=…  QA_P03_UPN=qa.p03@…
   ```

## 4. Local toolchain
- **Node.js 22.** The `dataapp` template README asks for v22; Rayfin itself needs 20+.
- Python 3.11+, Azure CLI, Git, VS Code + Claude Code (CLI or extension).
- `npm install -g @playwright/cli@latest`, for the template's visual validation.
- **Microsoft ODBC Driver 18 for SQL Server**, for `tools/fabric_query.py`. Installers are on Microsoft Learn;
  on macOS, use Homebrew `msodbcsql18`.
- `pip install -r requirements.txt`
- `az login --tenant <TENANT_ID> --allow-no-subscriptions`
- Optional: Java 17+ and `pip install pyspark` for `tools/run_notebooks_local.py`.
- `fabric.endpoints.json` (copy from `fabric.endpoints.example.json`, gitignored). It holds the SQL analytics
  endpoint host and the KQL Query URI. These are non-secret, so Claude Code may read the file.

## 5. Claude Code wiring
1. Open the repo root in VS Code and start Claude Code there.
2. Approve the project MCP servers from `.mcp.json` when prompted:
   - `fabric`: local Fabric MCP Server via `npx @microsoft/fabric-mcp@latest`. Docs/spec tools work offline;
     OneLake/core tools use your `az login`.
   - `microsoft-learn`: public Learn docs server (`https://learn.microsoft.com/api/mcp`), no auth.
3. You already added a Fabric MCP server in Claude Code. If it is the same local server under another name,
   remove one copy so Claude doesn't see duplicate tools: `claude mcp list`, then `claude mcp remove <n> --scope <scope>`.
4. Run `/context` and check that `CLAUDE.md` is listed under Memory files. Run `/skills` and check you see
   `dp700-lab`, `ambermoor-data`, `ask-ambermoor` and `rayfin-app`.
5. **Windows, native (not WSL):** if `fabric` shows ✘ Failed in `claude mcp list`, try
   `"command": "cmd", "args": ["/c", "npx", "-y", "@microsoft/fabric-mcp@latest", "server", "start", "--mode", "all"]`.
   Older Claude Code docs recommended this wrapper. *Verify* on your version.

## 6. Generate and load data (lab L1 does the load)
```bash
python tools/generate_ambermoor_data.py --out data/generated --seed 42
python tools/verify_golden.py --data data/generated      # expect 9× PASS
```

## 7. FT6: connect the published data agent to Claude Code
The data agent MCP endpoint has **no dynamic client registration**. You attach a Fabric bearer token
(scope `https://api.fabric.microsoft.com/.default`) yourself. `tools/fabric-token-header.mjs` does that through
Claude Code's `headersHelper`, reusing your `az login`. User scope keeps your token tooling out of the repo:
```bash
claude mcp add-json ambermoor-agent --scope user '{"type":"http","url":"https://api.fabric.microsoft.com/v1/mcp/workspaces/<WS_AGENT_ID>/dataagents/<AGENT_ID>/agent","headersHelper":"node <ABSOLUTE_PATH>/ambermoor-fabric-poc/tools/fabric-token-header.mjs"}'
claude mcp get ambermoor-agent
```
- Copy the exact URL from the agent's **Settings → Model Context Protocol** tab after publishing.
- Agent answers may leave Fabric's compliance boundary (Learn warning). This is acceptable here because the data
  is synthetic. It needs a governance decision for client data.

## FT4 note: launching from `app/`
Rayfin writes its own `app/.mcp.json` (`rayfin` server) and its docs say to run the agent from the Rayfin project
root. After scaffolding, start Claude Code from `app/`, then run `claude mcp list` there. If the repo-root servers
(`fabric`, `microsoft-learn`) don't show, add them at user scope or open a second window at the root. I haven't
verified how Claude Code resolves `.mcp.json` from a subfolder of a git repo.
