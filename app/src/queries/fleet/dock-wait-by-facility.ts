import query from "./dock-wait-by-facility.dax?raw";
import spec from "./dock-wait-by-facility.json";
import type { ColumnMetadataMap } from "@/lib/to-data-table";
import type { VisualizationSpec } from "@microsoft/fabric-visuals";

// Red bar = the facility has late trips caused by a dock wait over 2 h (golden Q9: P07 Monday foodservice).
// The bar averages all trips (P07 0.66 h); the tooltip adds the average over just those late trips (P07 6.26 h).
const columnMetadata: ColumnMetadataMap = {
    "dim_facility[facility_id]": { name: "facilityId", displayName: "Facility" },
    "[Avg Dock Wait (h)]": { name: "avgDockWait", displayName: "Avg dock wait (h)", format: "0.00" },
    "[Late Trip Dock Wait (h)]": { name: "lateDockWait", displayName: "Avg dock wait on late trips (h)", format: "0.00" },
    "[Dock-Delayed Late Trips]": { name: "dockDelayedLate", displayName: "Late trips caused by dock wait", format: "#,0" },
    "[Trips]": { name: "trips", displayName: "Trips", format: "#,0" },
};

export function dockWaitByFacilityQuery() {
    return { connection: "ambermoor", query, columnMetadata, vegaLiteSpec: spec as VisualizationSpec };
}
