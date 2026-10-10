import query from "./kpi-tiles.dax?raw";
import type { ColumnMetadataMap } from "@/lib/to-data-table";

// Headline KPI tiles (one row). Rendered as tiles, not a Vega visual, so there is no vegaLiteSpec to validate.
const columnMetadata: ColumnMetadataMap = {
    "[Cases Produced]": { name: "casesProduced", displayName: "Cases Produced", format: "#,0" },
    "[Waste Rate %]": { name: "wasteRate", displayName: "Waste Rate", format: "0.00%" },
    "[OTIF %]": { name: "otif", displayName: "OTIF", format: "0.0%" },
    "[Fill Rate %]": { name: "fillRate", displayName: "Fill Rate", format: "0.00%" },
    "[Excursion Shipments]": { name: "excursions", displayName: "Excursion Shipments", format: "#,0" },
    "[Shipments]": { name: "shipments", displayName: "Shipments", format: "#,0" },
};

export function kpiTilesQuery() {
    return { connection: "ambermoor", query, columnMetadata };
}
