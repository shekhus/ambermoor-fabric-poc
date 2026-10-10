import query from "./ontime-heatmap.dax?raw";
import spec from "./ontime-heatmap.json";
import type { ColumnMetadataMap } from "@/lib/to-data-table";
import type { VisualizationSpec } from "@microsoft/fabric-visuals";

// Low-cardinality channel filter (4 values): fetched at full grain, filtered client-side (query-design skill).
const columnMetadata: ColumnMetadataMap = {
    "dim_facility[facility_id]": { name: "facilityId", displayName: "Facility" },
    "dim_date[weekday]": { name: "weekday", displayName: "Weekday" },
    "dim_customer[channel]": { name: "channel", displayName: "Channel" },
    "[On Time %]": { name: "onTime", displayName: "On Time", format: "0.0%" },
    "[Shipments]": { name: "shipments", displayName: "Shipments", format: "#,0" },
};

export function ontimeHeatmapQuery() {
    return { connection: "ambermoor", query, columnMetadata, vegaLiteSpec: spec as VisualizationSpec };
}
