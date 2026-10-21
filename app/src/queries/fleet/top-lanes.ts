import query from "./top-lanes.dax?raw";
import spec from "./top-lanes.json";
import type { ColumnMetadataMap } from "@/lib/to-data-table";
import type { VisualizationSpec } from "@microsoft/fabric-visuals";

// Rendered as a DataGrid. The bar spec lets validate:visual check the query (golden Q10 top lanes).
const columnMetadata: ColumnMetadataMap = {
    "fact_trip[lane_id]": { name: "laneId", displayName: "Lane (facility->customer)" },
    "dim_customer[customer_name]": { name: "customer", displayName: "Customer" },
    "[Trips]": { name: "trips", displayName: "Trips", format: "#,0" },
    "[Trip Cost]": { name: "tripCost", displayName: "Trip cost", format: "$#,0" },
    "[Freight Cost per Case]": { name: "costPerCase", displayName: "Cost per case", format: "$#,0.00" },
    "[Avg Dock Wait (h)]": { name: "avgDockWait", displayName: "Avg dock wait (h)", format: "0.00" },
};

export function topLanesQuery() {
    return { connection: "ambermoor", query, columnMetadata, vegaLiteSpec: spec as VisualizationSpec };
}
