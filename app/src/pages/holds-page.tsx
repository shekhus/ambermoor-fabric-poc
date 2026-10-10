import { useCallback, useEffect, useState, type FormEvent } from "react";

import {
    addAction, addUpdate, listActions, listUpdates, setActionStatus, setHoldStatus,
    type ActionRow, type Hold, type HoldStatus, type HoldUpdateRow, type RootCause,
} from "@/services/holds.service";
import { Button, Empty, ErrorBanner, inputClass, Skeleton } from "@/components/ui";
import { cn } from "@/lib/utils";

const TABS: HoldStatus[] = ["Open", "Released", "Destroyed"];
const CAUSES: RootCause[] = ["Supplier", "Process", "Equipment", "People", "Other"];
const when = (d: string) => new Date(d).toLocaleString();

export function HoldsPage({ holds, isLoading, error, onChanged }: {
    holds: Hold[]; isLoading: boolean; error?: Error; onChanged: () => void;
}) {
    const [tab, setTab] = useState<HoldStatus>("Open");
    const [selectedId, setSelectedId] = useState<string | undefined>();
    const list = holds.filter((h) => h.status === tab);
    const selected = holds.find((h) => h.id === selectedId);

    return (
        <div className="grid grid-cols-1 gap-grid lg:grid-cols-5">
            <section className="flex flex-col gap-3 lg:col-span-2" aria-label="Holds">
                <div role="tablist" className="flex gap-1 rounded-lg border border-border bg-card p-1">
                    {TABS.map((t) => (
                        <button key={t} role="tab" type="button" aria-selected={tab === t} onClick={() => setTab(t)}
                            className={cn(
                                "flex-1 rounded-md px-3 py-1.5 text-300 font-medium focus:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                                tab === t ? "bg-primary text-primary-foreground" : "text-card-foreground hover:bg-hover",
                            )}>
                            {t} ({holds.filter((h) => h.status === t).length})
                        </button>
                    ))}
                </div>
                {error && <ErrorBanner error={error} />}
                {isLoading ? <Skeleton className="h-48" /> : list.length === 0 ? (
                    <Empty>No {tab.toLowerCase()} holds in your scope. Place one from Lot trace.</Empty>
                ) : (
                    <ul className="flex flex-col gap-2">
                        {list.map((h) => (
                            <li key={h.id}>
                                <button type="button" onClick={() => setSelectedId(h.id)}
                                    className={cn(
                                        "w-full rounded-xl border bg-card p-3 text-left shadow-2 hover:bg-hover focus:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                                        selectedId === h.id ? "border-primary" : "border-border",
                                    )}>
                                    <div className="flex items-center justify-between gap-2">
                                        <span className="font-[family-name:var(--font-monospace)] text-300 font-semibold text-card-foreground">{h.lot_id}</span>
                                        <SeverityBadge severity={h.severity} />
                                    </div>
                                    <div className="mt-1 text-200 text-muted-foreground">
                                        {h.facility_id} · {h.cases_on_hold} cases · {h.source_ref ?? "manual"} · {when(h.opened_at)}
                                    </div>
                                </button>
                            </li>
                        ))}
                    </ul>
                )}
            </section>
            <section className="lg:col-span-3" aria-label="Hold detail">
                {selected ? <HoldDetail key={selected.id} hold={selected} onChanged={onChanged} />
                    : <Empty>Select a hold to see its timeline and corrective actions.</Empty>}
            </section>
        </div>
    );
}

function SeverityBadge({ severity }: { severity: string }) {
    const hot = severity === "Critical" || severity === "High";
    return (
        <span className={cn("rounded-full px-2 py-0.5 text-200 font-semibold",
            hot ? "bg-destructive text-destructive-foreground" : "bg-secondary text-secondary-foreground")}>
            {severity}
        </span>
    );
}

function HoldDetail({ hold, onChanged }: { hold: Hold; onChanged: () => void }) {
    const [updates, setUpdates] = useState<HoldUpdateRow[]>([]);
    const [actions, setActions] = useState<ActionRow[]>([]);
    const [error, setError] = useState<string | undefined>();
    const [busy, setBusy] = useState(false);
    const [note, setNote] = useState("");
    const [action, setAction] = useState({ title: "", owner_upn: "", due_date: "", root_cause_category: "Supplier" as RootCause });

    const load = useCallback(async () => {
        try {
            const [u, a] = await Promise.all([listUpdates(hold.id), listActions(hold.id)]);
            setUpdates(u);
            setActions(a);
        } catch (err) {
            setError(err instanceof Error ? err.message : String(err));
        }
    }, [hold.id]);

    useEffect(() => { void load(); }, [load]);

    async function run(fn: () => Promise<void>) {
        setBusy(true);
        setError(undefined);
        try {
            await fn();
            await load();
            onChanged();
        } catch (err) {
            setError(err instanceof Error ? err.message : String(err));
        } finally {
            setBusy(false);
        }
    }

    function submitNote(e: FormEvent) {
        e.preventDefault();
        void run(async () => { await addUpdate(hold.id, note); setNote(""); });
    }

    function submitAction(e: FormEvent) {
        e.preventDefault();
        void run(async () => {
            await addAction(hold.id, action);
            setAction({ title: "", owner_upn: "", due_date: "", root_cause_category: "Supplier" });
        });
    }

    return (
        <div className="flex flex-col gap-grid rounded-xl border border-border bg-card p-4 shadow-2">
            <header className="flex flex-wrap items-start justify-between gap-3">
                <div>
                    <div className="font-[family-name:var(--font-monospace)] text-500 font-semibold text-card-foreground">{hold.lot_id}</div>
                    <div className="text-300 text-muted-foreground">
                        {hold.facility_id} · {hold.reason} · opened by {hold.opened_by} · {when(hold.opened_at)}
                    </div>
                </div>
                {hold.status === "Open" && (
                    <div className="flex gap-2">
                        <Button variant="secondary" disabled={busy} onClick={() => void run(() => setHoldStatus(hold, "Released"))}>Release</Button>
                        <Button variant="danger" disabled={busy} onClick={() => void run(() => setHoldStatus(hold, "Destroyed"))}>Destroy</Button>
                    </div>
                )}
            </header>
            {error && <ErrorBanner error={error} />}

            <div>
                <h3 className="mb-2 text-400 font-semibold text-card-foreground">Corrective actions</h3>
                {actions.length === 0 ? <p className="text-300 text-muted-foreground">None yet.</p> : (
                    <ul className="flex flex-col gap-2">
                        {actions.map((a) => (
                            <li key={a.id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border p-2 text-300">
                                <span className="text-card-foreground">
                                    <strong>{a.title}</strong> · {a.root_cause_category} · {a.owner_upn} · due {new Date(a.due_date).toLocaleDateString()}
                                </span>
                                <span className="flex items-center gap-2">
                                    <span className="text-muted-foreground">{a.status}</span>
                                    {a.status === "Open" && (
                                        <Button variant="secondary" disabled={busy} onClick={() => void run(() => setActionStatus(a, "Done"))}>Mark done</Button>
                                    )}
                                </span>
                            </li>
                        ))}
                    </ul>
                )}
                <form onSubmit={submitAction} className="mt-3 grid grid-cols-1 gap-2 md:grid-cols-5">
                    <input className={cn(inputClass, "md:col-span-2")} placeholder="Action title" maxLength={200} required
                        value={action.title} onChange={(e) => setAction({ ...action, title: e.target.value })} aria-label="Action title" />
                    <input className={inputClass} placeholder="Owner UPN" maxLength={120} required
                        value={action.owner_upn} onChange={(e) => setAction({ ...action, owner_upn: e.target.value })} aria-label="Owner" />
                    <input className={inputClass} type="date" required value={action.due_date}
                        onChange={(e) => setAction({ ...action, due_date: e.target.value })} aria-label="Due date" />
                    <select className={inputClass} value={action.root_cause_category} aria-label="Root cause"
                        onChange={(e) => setAction({ ...action, root_cause_category: e.target.value as RootCause })}>
                        {CAUSES.map((c) => <option key={c}>{c}</option>)}
                    </select>
                    <div className="md:col-span-5"><Button type="submit" disabled={busy}>Add corrective action</Button></div>
                </form>
            </div>

            <div>
                <h3 className="mb-2 text-400 font-semibold text-card-foreground">Timeline</h3>
                <form onSubmit={submitNote} className="mb-3 flex gap-2">
                    <input className={inputClass} placeholder="Add an update…" maxLength={1000} required value={note}
                        onChange={(e) => setNote(e.target.value)} aria-label="Update note" />
                    <Button type="submit" disabled={busy}>Post</Button>
                </form>
                <ol className="flex flex-col gap-2 border-l-2 border-brand pl-4">
                    {updates.map((u) => (
                        <li key={u.id} className="text-300">
                            <div className="text-card-foreground">{u.note}</div>
                            <div className="text-200 text-muted-foreground">{u.author} · {when(u.created_at)}</div>
                        </li>
                    ))}
                </ol>
            </div>
        </div>
    );
}
