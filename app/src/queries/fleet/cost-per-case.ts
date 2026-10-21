import query from "./cost-per-case.dax?raw";
import spec from "./cost-per-case.json";
import type { ColumnMetadataMap } from "@/lib/to-data-table";
import type { VisualizationSpec } from "@microsoft/fabric-visuals";

const columnMetadata: ColumnMetadataMap = {
    "dim_facility[facility_id]": { name: "facilityId", displayName: "Facility" },
    "[Freight Cost per Case]": { name: "costPerCase", displayName: "Freight cost per case", format: "$#,0.00" },
    "[Trip Cost]": { name: "tripCost", displayName: "Trip cost", format: "$#,0" },
};

export function costPerCaseQuery() {
    return { connection: "ambermoor", query, columnMetadata, vegaLiteSpec: spec as VisualizationSpec };
}
