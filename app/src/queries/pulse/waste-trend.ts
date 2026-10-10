import query from "./waste-trend.dax?raw";
import spec from "./waste-trend.json";
import type { ColumnMetadataMap } from "@/lib/to-data-table";
import type { VisualizationSpec } from "@microsoft/fabric-visuals";

const columnMetadata: ColumnMetadataMap = {
    "dim_date[year_month]": { name: "yearMonth", displayName: "Month" },
    "dim_facility[facility_id]": { name: "facilityId", displayName: "Facility" },
    "[Waste Rate %]": { name: "wasteRate", displayName: "Waste Rate", format: "0.00%" },
};

export function wasteTrendQuery() {
    return { connection: "ambermoor", query, columnMetadata, vegaLiteSpec: spec as VisualizationSpec };
}
