import type { RayfinClient } from "@microsoft/rayfin-client";

import { getRayfinClient } from "@/lib/rayfin-client";
import type { AmbermoorAppSchema } from "../../rayfin/data/schema";
import type { AppFunctionsSchema } from "../../rayfin/functions/src/types";

// "Ask Ambermoor": the Rayfin function askAmbermoor sends the question + model names to Claude and returns DAX.
// The page then runs that DAX itself, as the signed-in user, so row-level security shapes the answer.

export type AskAnswer = AppFunctionsSchema["askAmbermoor"]["output"];

function client(): RayfinClient<AmbermoorAppSchema, AppFunctionsSchema> {
    return getRayfinClient() as unknown as RayfinClient<AmbermoorAppSchema, AppFunctionsSchema>;
}

/** previousDax/previousError: pass a failed query back once so Claude can fix it. */
export function askAmbermoor(question: string, previousDax = "", previousError = ""): Promise<AskAnswer> {
    return client().functions.askAmbermoor.invoke({ question, previousDax, previousError }, { timeoutMs: 120_000 });
}
