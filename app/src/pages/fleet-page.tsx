import { VegaVisual } from "@microsoft/fabric-visuals";
import { DataGrid } from "@microsoft/fabric-datagrid";
import { ExternalLink } from "lucide-react";

import { useThemeContext } from "@/hooks/theme.context";
import { fleet } from "@/queries";
import { cell, ErrorBanner, fmt, Kpi, Skeleton, useTable } from "@/components/ui";

const kpiDef = fleet.fleetKpisQuery();
const dockDef = fleet.dockWaitByFacilityQuery();
const costDef = fleet.costPerCaseQuery();
const lanesDef = fleet.topLanesQuery();

// Live truck positions stay in the Eventhouse (Real-Time Dashboard RTD_Ambermoor_Fleet); this page is trip history
// from the semantic model, so RLS scopes it like every other page. Set the dashboard link in .env.production.local (VITE_FLEET_MAP_URL).
const LIVE_MAP_URL = import.meta.env.VITE_FLEET_MAP_URL;

/** showLiveMap: network users only. The dashboard reads the Eventhouse, which has no RLS, and lives in DEV. */
export function FleetPage({ showLiveMap }: { showLiveMap: boolean }) {
    const { theme } = useThemeContext();
    const kpis = useTable(kpiDef);
    const dock = useTable(dockDef);
    const cost = useTable(costDef);
    const lanes = useTable(lanesDef);

    const m = kpiDef.columnMetadata;
    const k = (name: string, key: string) => fmt(cell(kpis.table, name), m[key].format);
    const dockLate = Number(cell(kpis.table, "dockDelayedLate") ?? 0);

    return (
        <div className="flex flex-col gap-grid">
            {kpis.error && <ErrorBanner error={kpis.error} />}
            <section className="grid grid-cols-2 gap-grid md:grid-cols-3 xl:grid-cols-5" aria-label="Fleet KPIs">
                <Kpi label="Trips" value={k("trips", "[Trips]")} hint="One per shipment" loading={kpis.isLoading} />
                <Kpi label="Trip cost" value={k("tripCost", "[Trip Cost]")} hint="Km × rate + driver hours"
                    loading={kpis.isLoading} />
                <Kpi label="Freight cost per case" value={k("costPerCase", "[Freight Cost per Case]")}
                    loading={kpis.isLoading} />
                <Kpi label="Avg dock wait" value={`${k("avgDockWait", "[Avg Dock Wait (h)]")} h`}
                    hint="Planned → actual departure" loading={kpis.isLoading} />
                <Kpi label="Late trips caused by dock wait" value={k("dockDelayedLate", "[Dock-Delayed Late Trips]")}
                    hint="Late and waited > 2 h at the dock" tone={dockLate > 0 ? "alert" : "good"} loading={kpis.isLoading} />
            </section>

            <section className="grid grid-cols-1 gap-grid lg:grid-cols-2">
                <div className="min-h-80">
                    {dock.error ? <ErrorBanner error={dock.error} /> : !dock.table ? <Skeleton className="h-80" /> : (
                        <VegaVisual spec={dockDef.vegaLiteSpec} data={dock.table} theme={theme}
                            header={{ title: "Dock wait by facility", subtitle: "Red = late trips caused by dock wait" }} />
                    )}
                </div>
                <div className="min-h-80">
                    {cost.error ? <ErrorBanner error={cost.error} /> : !cost.table ? <Skeleton className="h-80" /> : (
                        <VegaVisual spec={costDef.vegaLiteSpec} data={cost.table} theme={theme}
                            header={{ title: "Freight cost per case", subtitle: "By ship-from facility" }} />
                    )}
                </div>
            </section>

            <section className="flex flex-col gap-3">
                {LIVE_MAP_URL && showLiveMap && (
                    <a href={LIVE_MAP_URL} target="_blank" rel="noreferrer"
                        className="flex w-fit items-center gap-2 rounded-lg border border-primary bg-card px-3 py-1.5 text-300 font-medium text-card-foreground hover:bg-hover focus:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                        <ExternalLink className="icon-size-200 text-primary" aria-hidden />
                        Live truck map and reefer temperatures
                    </a>
                )}
                <div className="min-h-80">
                    {lanes.error ? <ErrorBanner error={lanes.error} /> : !lanes.table ? <Skeleton className="h-80" /> : (
                        <DataGrid data={lanes.table} theme={theme}
                            header={{ title: "Top 10 lanes by trip cost", subtitle: "Facility → customer" }} />
                    )}
                </div>
            </section>
        </div>
    );
}
