import { useMemo, useState, type FormEvent } from "react";
import { VegaVisual } from "@microsoft/fabric-visuals";
import { DataGrid } from "@microsoft/fabric-datagrid";
import type { InteractionEvent } from "@microsoft/fabric-visuals-core";

import { useThemeContext } from "@/hooks/theme.context";
import { trace } from "@/queries";
import { createHold, type Severity } from "@/services/holds.service";
import { Button, cell, Empty, ErrorBanner, fmt, inputClass, Kpi, rowsAsObjects, Skeleton, useTable } from "@/components/ui";

const noticesDef = trace.supplierNoticesQuery();
const SEVERITIES: Severity[] = ["Low", "Medium", "High", "Critical"];
const ID_RE = /^[A-Za-z0-9_-]{1,60}$/;

interface Lot { lotId: string; facilityId: string; sku: string; casesProduced: number; casesShipped: number }

export function TracePage({ facilityIds, onHoldsChanged }: { facilityIds: string[] | undefined; onHoldsChanged: () => void }) {
    const notices = useTable(noticesDef);
    const firstNotice = rowsAsObjects(notices.table)[0];
    const [input, setInput] = useState("");
    const [lotId, setLotId] = useState<string | undefined>();
    const active = lotId ?? (firstNotice?.ingredientLotId as string | undefined);
    const sourceRef = active && firstNotice?.ingredientLotId === active ? String(firstNotice.noticeId) : undefined;

    function search(e: FormEvent) {
        e.preventDefault();
        if (ID_RE.test(input.trim())) setLotId(input.trim());
    }

    return (
        <div className="flex flex-col gap-grid">
            <section className="flex flex-col gap-3 rounded-xl border border-border bg-card p-4 shadow-2">
                <form onSubmit={search} className="flex flex-wrap items-end gap-3">
                    <label className="flex min-w-72 flex-1 flex-col gap-1 text-300 text-muted-foreground">
                        Ingredient lot
                        <input className={inputClass} value={input} onChange={(e) => setInput(e.target.value)}
                            placeholder="e.g. ILOT-P02-ING02-20260908" aria-invalid={!!input && !ID_RE.test(input.trim())} />
                    </label>
                    <Button type="submit" disabled={!ID_RE.test(input.trim())}>Trace</Button>
                </form>
                <div className="flex flex-wrap items-center gap-2 text-200 text-muted-foreground">
                    Supplier notices:
                    {notices.error && <span className="text-destructive">{notices.error.message}</span>}
                    {rowsAsObjects(notices.table).map((n) => (
                        <button key={String(n.noticeId)} type="button"
                            onClick={() => { setLotId(String(n.ingredientLotId)); setInput(String(n.ingredientLotId)); }}
                            className="rounded-full border border-destructive px-3 py-1 font-medium text-destructive hover:bg-hover focus:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                            {String(n.noticeId)} · {String(n.ingredientLotId)} · {String(n.status)}
                        </button>
                    ))}
                </div>
            </section>
            {active ? <TraceResults key={active} ingredientLotId={active} sourceRef={sourceRef}
                facilityIds={facilityIds} onHoldsChanged={onHoldsChanged} />
                : notices.isLoading ? <Skeleton className="h-40" /> : <Empty>Enter an ingredient lot to trace.</Empty>}
        </div>
    );
}

function TraceResults({ ingredientLotId, sourceRef, facilityIds, onHoldsChanged }: {
    ingredientLotId: string; sourceRef?: string; facilityIds: string[] | undefined; onHoldsChanged: () => void;
}) {
    const { theme } = useThemeContext();
    const defs = useMemo(() => ({
        summary: trace.traceSummaryQuery({ ingredientLotId }),
        lots: trace.traceLotsQuery({ ingredientLotId }),
        customers: trace.traceCustomersQuery({ ingredientLotId }),
    }), [ingredientLotId]);
    const summary = useTable(defs.summary);
    const lots = useTable(defs.lots);
    const customers = useTable(defs.customers);
    const [selected, setSelected] = useState<Lot | undefined>();

    const sm = defs.summary.columnMetadata;
    const s = (name: string, key: string) => fmt(cell(summary.table, name), sm[key].format);
    const lotRows = rowsAsObjects(lots.table) as unknown as Lot[];

    function onLotInteraction(events: InteractionEvent[]) {
        for (const ev of events) {
            if (ev.action === "clear") setSelected(undefined);
            else {
                const p = ev.selections[0]?.predicates.find((x) => x.name === "lotId");
                const id = p && p.type === "set" ? String(p.values[0]) : undefined;
                setSelected(lotRows.find((l) => l.lotId === id));
            }
        }
    }

    return (
        <>
            {summary.error && <ErrorBanner error={summary.error} />}
            <section className="grid grid-cols-2 gap-grid md:grid-cols-4" aria-label="Recall scope">
                <Kpi label="Finished lots" value={s("lots", "[Finished Lots]")} loading={summary.isLoading} />
                <Kpi label="Cases shipped" value={s("casesShipped", "[Cases Shipped]")} loading={summary.isLoading} tone="alert" />
                <Kpi label="Customers" value={s("customers", "[Customers]")} hint={`${s("shipments", "[Shipments]")} shipments`}
                    loading={summary.isLoading} />
                <Kpi label="Cases destroyed" value={s("casesDestroyed", "[Cases Destroyed]")} hint="Waste reason: Supplier Recall"
                    loading={summary.isLoading} />
            </section>
            <section className="grid grid-cols-1 gap-grid xl:grid-cols-5">
                <div className="flex min-h-96 flex-col gap-3 xl:col-span-3">
                    {lots.error ? <ErrorBanner error={lots.error} /> : !lots.table ? <Skeleton className="h-96" /> : (
                        <DataGrid data={lots.table} theme={theme} onInteraction={onLotInteraction}
                            header={{ title: "Finished lots", subtitle: "Select a lot to place it on hold" }} />
                    )}
                    {selected && (
                        <PlaceHold lot={selected} sourceRef={sourceRef} canWrite={!!facilityIds?.includes(selected.facilityId)}
                            onDone={() => { setSelected(undefined); onHoldsChanged(); }} />
                    )}
                </div>
                <div className="min-h-96 xl:col-span-2">
                    {customers.error ? <ErrorBanner error={customers.error} /> : !customers.table ? <Skeleton className="h-96" /> : (
                        <VegaVisual spec={defs.customers.vegaLiteSpec} data={customers.table} theme={theme}
                            header={{ title: "Customers in scope", subtitle: "Cases shipped from affected lots" }} />
                    )}
                </div>
            </section>
        </>
    );
}

function PlaceHold({ lot, sourceRef, canWrite, onDone }: { lot: Lot; sourceRef?: string; canWrite: boolean; onDone: () => void }) {
    const [reason, setReason] = useState(sourceRef ? `Supplier notice ${sourceRef}` : "");
    const [severity, setSeverity] = useState<Severity>("High");
    const [cases, setCases] = useState(String(Math.max(0, (lot.casesProduced ?? 0) - (lot.casesShipped ?? 0))));
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState<string | undefined>();

    async function submit(e: FormEvent) {
        e.preventDefault();
        setBusy(true);
        setError(undefined);
        try {
            await createHold({
                lot_id: lot.lotId, facility_id: lot.facilityId, reason: reason.slice(0, 200), severity,
                cases_on_hold: Math.max(0, Math.round(Number(cases) || 0)), source_ref: sourceRef,
            });
            onDone();
        } catch (err) {
            setError(err instanceof Error ? err.message : String(err));
        } finally {
            setBusy(false);
        }
    }

    return (
        <form onSubmit={submit} className="flex flex-col gap-3 rounded-xl border border-primary bg-card p-4 shadow-4"
            aria-label={`Place hold on ${lot.lotId}`}>
            <div className="text-400 font-semibold text-card-foreground">
                Place hold · {lot.lotId} <span className="text-300 font-normal text-muted-foreground">({lot.facilityId}, {lot.sku})</span>
            </div>
            {!canWrite && <ErrorBanner error="This lot belongs to a facility outside your scope." />}
            <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
                <label className="flex flex-col gap-1 text-300 text-muted-foreground md:col-span-2">Reason
                    <input className={inputClass} value={reason} maxLength={200} required onChange={(e) => setReason(e.target.value)} />
                </label>
                <label className="flex flex-col gap-1 text-300 text-muted-foreground">Severity
                    <select className={inputClass} value={severity} onChange={(e) => setSeverity(e.target.value as Severity)}>
                        {SEVERITIES.map((s) => <option key={s}>{s}</option>)}
                    </select>
                </label>
                <label className="flex flex-col gap-1 text-300 text-muted-foreground">Cases on hold
                    <input className={inputClass} type="number" min={0} value={cases} onChange={(e) => setCases(e.target.value)} />
                </label>
            </div>
            {error && <ErrorBanner error={error} />}
            <div className="flex gap-2">
                <Button type="submit" disabled={busy || !canWrite || !reason.trim()}>{busy ? "Saving…" : "Place hold"}</Button>
                <Button variant="secondary" onClick={onDone}>Cancel</Button>
            </div>
        </form>
    );
}
