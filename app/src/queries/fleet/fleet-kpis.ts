import query from "./fleet-kpis.dax?raw";
import type { ColumnMetadataMap } from "@/lib/to-data-table";

// Fleet headline tiles (one row). Rendered as tiles, not a Vega visual, so there is no vegaLiteSpec to validate.
const columnMetadata: ColumnMetadataMap = {
    "[Trips]": { name: "trips", displayName: "Trips", format: "#,0" },
    "[Trip Cost]": { name: "tripCost", displayName: "Trip cost", format: "$#,0" },
    "[Freight Cost per Case]": { name: "costPerCase", displayName: "Freight cost per case", format: "$#,0.00" },
    "[Avg Dock Wait (h)]": { name: "avgDockWait", displayName: "Avg dock wait (h)", format: "0.00" },
    "[Dock-Delayed Late Trips]": { name: "dockDelayedLate", displayName: "Late trips caused by dock wait", format: "#,0" },
};

export function fleetKpisQuery() {
    return { connection: "ambermoor", query, columnMetadata };
}
