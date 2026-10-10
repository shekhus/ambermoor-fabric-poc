import { useState } from "react";
import { Moon, Snowflake, Sun } from "lucide-react";

import { useThemeContext } from "@/hooks/theme.context";
import { useHolds } from "@/hooks/use-holds";
import { scope } from "@/queries";
import { rowsAsObjects, useTable } from "@/components/ui";
import { PulsePage } from "@/pages/pulse-page";
import { TracePage } from "@/pages/trace-page";
import { HoldsPage } from "@/pages/holds-page";
import { cn } from "@/lib/utils";

const facilitiesDef = scope.myFacilitiesQuery();
const PAGES = [
    { id: "pulse", label: "Plant pulse" },
    { id: "trace", label: "Lot trace" },
    { id: "holds", label: "Holds & actions" },
] as const;
type PageId = (typeof PAGES)[number]["id"];

function App() {
    const { isDark, toggleTheme } = useThemeContext();
    const [page, setPage] = useState<PageId>("pulse");

    // Facilities visible to this user via the model's RLS; used to scope writeback rows.
    const facilities = useTable(facilitiesDef);
    const facilityRows = rowsAsObjects(facilities.table);
    const facilityIds = facilities.table ? facilityRows.map((f) => String(f.facilityId)) : undefined;
    const holds = useHolds(facilityIds);
    const openHolds = holds.holds.filter((h) => h.status === "Open").length;
    const scopeLabel = !facilityIds ? "…" : facilityIds.length === 1
        ? `${facilityIds[0]} · ${String(facilityRows[0].facilityName)}` : `Network · ${facilityIds.length} facilities`;

    return (
        <div className="min-h-screen bg-background text-foreground">
            <div className="h-1 w-full bg-gradient-to-r from-brand via-primary to-destructive" aria-hidden />
            <div className="mx-auto flex max-w-screen-2xl flex-col gap-grid p-4 md:p-6">
                <header className="flex flex-wrap items-center justify-between gap-4">
                    <div className="flex items-center gap-3">
                        <div className="rounded-xl bg-brand p-2 text-brand-foreground"><Snowflake className="icon-size-300" aria-hidden /></div>
                        <div>
                            <h1 className="font-page-title text-500 font-semibold">Freshness Command Center</h1>
                            <p className="font-page-subtitle text-300 text-muted-foreground">
                                Ambermoor Fresh Foods (fictional, synthetic data) · Jul–Sep 2026 · Scope: {scopeLabel}
                            </p>
                        </div>
                    </div>
                    <div className="flex items-center gap-2">
                        <nav role="tablist" aria-label="Pages" className="flex gap-1 rounded-lg border border-border bg-card p-1">
                            {PAGES.map((p) => (
                                <button key={p.id} role="tab" type="button" aria-selected={page === p.id} onClick={() => setPage(p.id)}
                                    className={cn(
                                        "rounded-md px-3 py-1.5 text-300 font-medium focus:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                                        page === p.id ? "bg-primary text-primary-foreground" : "text-card-foreground hover:bg-hover",
                                    )}>
                                    {p.label}
                                    {p.id === "holds" && openHolds > 0 && (
                                        <span className="ml-2 rounded-full bg-destructive px-1.5 text-200 text-destructive-foreground">{openHolds}</span>
                                    )}
                                </button>
                            ))}
                        </nav>
                        <button type="button" onClick={toggleTheme} aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
                            className="rounded-lg border border-border bg-card p-2 text-card-foreground hover:bg-hover focus:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                            {isDark ? <Sun className="icon-size-200" /> : <Moon className="icon-size-200" />}
                        </button>
                    </div>
                </header>

                {page === "pulse" && <PulsePage openHolds={openHolds} holdsLoading={holds.isLoading} />}
                {page === "trace" && <TracePage facilityIds={facilityIds} onHoldsChanged={() => void holds.refetch()} />}
                {page === "holds" && (
                    <HoldsPage holds={holds.holds} isLoading={holds.isLoading} error={holds.error}
                        onChanged={() => void holds.refetch()} />
                )}
            </div>
        </div>
    );
}

export default App;
