import type { RayfinClient } from "@microsoft/rayfin-client";

import { getRayfinClient } from "@/lib/rayfin-client";
import type { FreshyFreshAppSchema } from "../../rayfin/data/schema";
import type { AppFunctionsSchema } from "../../rayfin/functions/src/types";

// "Ask FreshyFresh": the Rayfin function askFreshyFresh sends the question + model names to Claude and returns DAX.
// The page then runs that DAX itself, as the signed-in user, so row-level security shapes the answer.

export type AskAnswer = AppFunctionsSchema["askFreshyFresh"]["output"];

function client(): RayfinClient<FreshyFreshAppSchema, AppFunctionsSchema> {
    return getRayfinClient() as unknown as RayfinClient<FreshyFreshAppSchema, AppFunctionsSchema>;
}

/** previousDax/previousError: pass a failed query back once so Claude can fix it. */
export function askFreshyFresh(question: string, previousDax = "", previousError = ""): Promise<AskAnswer> {
    return client().functions.askFreshyFresh.invoke({ question, previousDax, previousError }, { timeoutMs: 120_000 });
}
