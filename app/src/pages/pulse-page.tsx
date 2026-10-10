import { useMemo, useState } from "react";
import { VegaVisual } from "@microsoft/fabric-visuals";
import { filterRows } from "@microsoft/fabric-visuals-core";

import { useThemeContext } from "@/hooks/theme.context";
import { pulse } from "@/queries";
import { cell, ErrorBanner, fmt, Kpi, Skeleton, useTable } from "@/components/ui";
import { cn } from "@/lib/utils";

const kpiDef = pulse.kpiTilesQuery();
const wasteDef = pulse.wasteTrendQuery();
const skuDef = pulse.topWasteSkusQuery();
const heatDef = pulse.ontimeHeatmapQuery();
const CHANNELS = ["Foodservice", "Retail Grocery", "Club", "Convenience"];

export function PulsePage({ openHolds, holdsLoading }: { openHolds: number; holdsLoading: boolean }) {
    const { theme } = useThemeContext();
    const kpis = useTable(kpiDef);
    const waste = useTable(wasteDef);
    const skus = useTable(skuDef);
    const heat = useTable(heatDef);
    const [channel, setChannel] = useState("Foodservice");

    const heatForChannel = useMemo(() => {
        if (!heat.table) return undefined;
        const i = heat.table.columns.findIndex((c) => c.name === "channel");
        return filterRows(heat.table, (row) => row[i] === channel);
    }, [heat.table, channel]);

    const m = kpiDef.columnMetadata;
    const k = (name: string, key: string) => fmt(cell(kpis.table, name), m[key].format);
    const excursions = Number(cell(kpis.table, "excursions") ?? 0);

    return (
        <div className="flex flex-col gap-grid">
            {kpis.error && <ErrorBanner error={kpis.error} />}
            <section className="grid grid-cols-2 gap-grid md:grid-cols-3 xl:grid-cols-6" aria-label="Headline KPIs">
                <Kpi label="Cases produced" value={k("casesProduced", "[Cases Produced]")} loading={kpis.isLoading} />
                <Kpi label="Waste rate" value={k("wasteRate", "[Waste Rate %]")} hint="Aged out + damaged + QA reject"
                    loading={kpis.isLoading} />
                <Kpi label="OTIF" value={k("otif", "[OTIF %]")} hint="≤ requested + 1 h, all lines in full"
                    loading={kpis.isLoading} />
                <Kpi label="Fill rate" value={k("fillRate", "[Fill Rate %]")} tone="good" loading={kpis.isLoading} />
                <Kpi label="Cold-chain excursions" value={k("excursions", "[Excursion Shipments]")}
                    hint="≥ 30 min cumulative > 5 °C" tone={excursions > 0 ? "alert" : "good"} loading={kpis.isLoading} />
                <Kpi label="Open holds" value={holdsLoading ? "…" : String(openHolds)} hint="From app writeback"
                    tone={openHolds > 0 ? "alert" : "default"} />
            </section>

            <section className="grid grid-cols-1 gap-grid lg:grid-cols-5">
                <div className="min-h-80 lg:col-span-3">
                    {waste.error ? <ErrorBanner error={waste.error} /> : !waste.table ? <Skeleton className="h-80" /> : (
                        <VegaVisual spec={wasteDef.vegaLiteSpec} data={waste.table} theme={theme}
                            header={{ title: "Waste rate by month", subtitle: "Per production facility" }} />
                    )}
                </div>
                <div className="min-h-80 lg:col-span-2">
                    {skus.error ? <ErrorBanner error={skus.error} /> : !skus.table ? <Skeleton className="h-80" /> : (
                        <VegaVisual spec={skuDef.vegaLiteSpec} data={skus.table} theme={theme}
                            header={{ title: "Top 5 waste SKUs", subtitle: "Cases by reason" }} />
                    )}
                </div>
            </section>

            <section className="flex flex-col gap-3">
                <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Channel">
                    <span className="text-300 text-muted-foreground">Channel:</span>
                    {CHANNELS.map((c) => (
                        <button key={c} type="button" onClick={() => setChannel(c)} aria-pressed={channel === c}
                            className={cn(
                                "rounded-full border px-3 py-1 text-200 font-medium focus:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                                channel === c ? "border-primary bg-primary text-primary-foreground"
                                    : "border-border bg-card text-card-foreground hover:bg-hover",
                            )}>
                            {c}
                        </button>
                    ))}
                </div>
                <div className="min-h-96">
                    {heat.error ? <ErrorBanner error={heat.error} /> : !heatForChannel ? <Skeleton className="h-96" /> : (
                        <VegaVisual spec={heatDef.vegaLiteSpec} data={heatForChannel} theme={theme}
                            header={{ title: `On-time delivery: ${channel}`, subtitle: "Facility × requested delivery day" }} />
                    )}
                </div>
            </section>
        </div>
    );
}
