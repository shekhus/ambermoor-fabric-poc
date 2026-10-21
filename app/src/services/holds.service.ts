import type { RayfinClient } from "@microsoft/rayfin-client";

import { getRayfinClient } from "@/lib/rayfin-client";
import type { FreshyFreshAppSchema } from "../../rayfin/data/schema";

// Writeback to the app's Fabric SQL database through Rayfin entities (rayfin/data/*.ts).
// Lists use .first(500).execute(): fine for the POC's volumes. Switch to executePaginated() before real use.

export type HoldStatus = "Open" | "Released" | "Destroyed";
/** Set only by the Tutorial reset; archived holds stay in the database for audit but are not listed. */
const ARCHIVED = "Archived";
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

function client(): RayfinClient<FreshyFreshAppSchema> {
    return getRayfinClient() as unknown as RayfinClient<FreshyFreshAppSchema>;
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
    return (rows as unknown as (Omit<Hold, "status"> & { status: string })[])
        .filter((h): h is Hold => h.status !== ARCHIVED);
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
    // A typo like year 0004 saves in SQL but breaks the semantic model (Direct Lake can't load dates before 1900).
    const due = new Date(input.due_date);
    const year = due.getFullYear();
    const thisYear = new Date().getFullYear();
    if (Number.isNaN(due.getTime()) || year < thisYear - 1 || year > thisYear + 5) {
        throw new Error(`Due date ${input.due_date} looks wrong: pick a date between ${thisYear - 1} and ${thisYear + 5}.`);
    }
    await client().data.CorrectiveAction.create({
        hold: { id: holdId },
        title: input.title,
        owner_upn: input.owner_upn,
        due_date: due,
        status: "Open",
        root_cause_category: input.root_cause_category,
    } as never);
    await addUpdate(holdId, `Corrective action added: ${input.title}`);
}

export async function setActionStatus(action: ActionRow, status: ActionStatus): Promise<void> {
    await client().data.CorrectiveAction.update({ id: action.id }, { status });
    await addUpdate(action.hold_id, `Action "${action.title}" → ${status}`);
}

/**
 * Tutorial reset: holds are an audit trail (no deletes), so "reset" archives every hold the signed-in user opened
 * (Open, Released or Destroyed), cancels their open actions and logs the old status on each timeline. Archived holds
 * stay in the database but the app no longer lists them, so the next person starts from 0 in every tab.
 */
export async function resetMyHolds(holds: Hold[]): Promise<number> {
    const me = currentUser();
    const mine = holds.filter((h) => h.opened_by === me);
    for (const h of mine) {
        for (const a of await listActions(h.id)) {
            if (a.status === "Open") await client().data.CorrectiveAction.update({ id: a.id }, { status: "Cancelled" });
        }
        await client().data.QualityHold.update({ id: h.id }, { status: ARCHIVED });
        await addUpdate(h.id, `Archived by Tutorial reset (demo clean-up); status was ${h.status}`);
    }
    return mine.length;
}
