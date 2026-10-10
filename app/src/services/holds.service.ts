import type { RayfinClient } from "@microsoft/rayfin-client";

import { getRayfinClient } from "@/lib/rayfin-client";
import type { AmbermoorAppSchema } from "../../rayfin/data/schema";

// Writeback to the app's Fabric SQL database through Rayfin entities (rayfin/data/*.ts).
// Lists use .first(500).execute(): fine for the POC's volumes. Switch to executePaginated() before real use.

export type HoldStatus = "Open" | "Released" | "Destroyed";
export type Severity = "Low" | "Medium" | "High" | "Critical";
export type ActionStatus = "Open" | "Done" | "Cancelled";
export type RootCause = "Supplier" | "Process" | "Equipment" | "People" | "Other";

export interface Hold {
    id: string;
    lot_id: string;
    facility_id: string;
    reason: string;
    severity: Severity;
    status: HoldStatus;
    cases_on_hold: number;
    source_ref?: string;
    opened_by: string;
    opened_at: string;
}

export interface HoldUpdateRow {
    id: string;
    hold_id: string;
    note: string;
    author: string;
    created_at: string;
}

export interface ActionRow {
    id: string;
    hold_id: string;
    title: string;
    owner_upn: string;
    due_date: string;
    status: ActionStatus;
    root_cause_category: RootCause;
}

function client(): RayfinClient<AmbermoorAppSchema> {
    return getRayfinClient() as unknown as RayfinClient<AmbermoorAppSchema>;
}

export function currentUser(): string {
    const session = client().auth.getSession();
    if (!session.isAuthenticated || !session.user) {
        throw new Error("Not signed in.");
    }
    return session.user.email || session.user.id;
}

export async function listHolds(): Promise<Hold[]> {
    const rows = await client()
        .data.QualityHold.select([
            "id", "lot_id", "facility_id", "reason", "severity", "status", "cases_on_hold", "source_ref",
            "opened_by", "opened_at",
        ])
        .orderBy({ opened_at: "desc" })
        .first(500)
        .execute();
    return rows as unknown as Hold[];
}

export async function createHold(input: Omit<Hold, "id" | "status" | "opened_by" | "opened_at">): Promise<void> {
    const author = currentUser();
    const hold = (await client().data.QualityHold.create({
        ...input,
        status: "Open",
        opened_by: author,
        opened_at: new Date(),
    })) as unknown as Hold;
    await addUpdate(hold.id, `Hold opened: ${input.reason}`);
}

export async function setHoldStatus(hold: Hold, status: HoldStatus): Promise<void> {
    await client().data.QualityHold.update({ id: hold.id }, { status });
    await addUpdate(hold.id, `Status changed ${hold.status} → ${status}`);
}

export async function listUpdates(holdId: string): Promise<HoldUpdateRow[]> {
    const rows = await client()
        .data.HoldUpdate.select(["id", "hold_id", "note", "author", "created_at"])
        .where({ hold_id: { eq: holdId } })
        .orderBy({ created_at: "desc" })
        .first(500)
        .execute();
    return rows as unknown as HoldUpdateRow[];
}

export async function addUpdate(holdId: string, note: string): Promise<void> {
    await client().data.HoldUpdate.create({
        hold: { id: holdId },
        note: note.slice(0, 1000),
        author: currentUser(),
        created_at: new Date(),
    } as never);
}

export async function listActions(holdId: string): Promise<ActionRow[]> {
    const rows = await client()
        .data.CorrectiveAction.select(["id", "hold_id", "title", "owner_upn", "due_date", "status", "root_cause_category"])
        .where({ hold_id: { eq: holdId } })
        .orderBy({ due_date: "asc" })
        .first(500)
        .execute();
    return rows as unknown as ActionRow[];
}

export async function addAction(
    holdId: string,
    input: { title: string; owner_upn: string; due_date: string; root_cause_category: RootCause },
): Promise<void> {
    await client().data.CorrectiveAction.create({
        hold: { id: holdId },
        title: input.title,
        owner_upn: input.owner_upn,
        due_date: new Date(input.due_date),
        status: "Open",
        root_cause_category: input.root_cause_category,
    } as never);
    await addUpdate(holdId, `Corrective action added: ${input.title}`);
}

export async function setActionStatus(action: ActionRow, status: ActionStatus): Promise<void> {
    await client().data.CorrectiveAction.update({ id: action.id }, { status });
    await addUpdate(action.hold_id, `Action "${action.title}" → ${status}`);
}
