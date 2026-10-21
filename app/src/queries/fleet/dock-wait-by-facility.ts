import query from "./dock-wait-by-facility.dax?raw";
import spec from "./dock-wait-by-facility.json";
import type { ColumnMetadataMap } from "@/lib/to-data-table";
import type { VisualizationSpec } from "@microsoft/fabric-visuals";

// Red bar = the facility has late trips caused by a dock wait over 2 h (golden Q9: P07 Monday foodservice).
const columnMetadata: ColumnMetadataMap = {
    "dim_facility[facility_id]": { name: "facilityId", displayName: "Facility" },
    "[Avg Dock Wait (h)]": { name: "avgDockWait", displayName: "Avg dock wait (h)", format: "0.00" },
    "[Dock-Delayed Late Trips]": { name: "dockDelayedLate", displayName: "Late trips caused by dock wait", format: "#,0" },
    "[Trips]": { name: "trips", displayName: "Trips", format: "#,0" },
};

export function dockWaitByFacilityQuery() {
    return { connection: "ambermoor", query, columnMetadata, vegaLiteSpec: spec as VisualizationSpec };
}
