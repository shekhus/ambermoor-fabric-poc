#!/usr/bin/env node
// headersHelper for Claude Code MCP servers that need a Fabric bearer token (e.g. the published data agent MCP
// endpoint, which has no dynamic client registration). Prints {"Authorization":"Bearer <token>"} to stdout.
//
// Uses your Azure CLI sign-in:  az login --tenant <TENANT_ID> --allow-no-subscriptions
// Claude Code re-runs this on every (re)connect and after a 401, so expired tokens refresh themselves.
// Never log the token anywhere else.
import { execFileSync } from "node:child_process";

const isWindows = process.platform === "win32";
try {
  const token = execFileSync(
    isWindows ? "az.cmd" : "az",
    ["account", "get-access-token", "--resource", "https://api.fabric.microsoft.com", "--query", "accessToken", "-o", "tsv"],
    { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"], shell: isWindows, timeout: 9000 },
  ).trim();
  if (!token) throw new Error("empty token");
  process.stdout.write(JSON.stringify({ Authorization: `Bearer ${token}` }));
} catch {
  process.stderr.write("fabric-token-header: could not get a Fabric token. Run `az login` (right tenant) and retry.\n");
  process.exit(1);
}
