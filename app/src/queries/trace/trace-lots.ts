import template from "./trace-lots.dax?raw";
import spec from "./trace-lots.json";
import { fill } from "./dax-param";
import type { ColumnMetadataMap } from "@/lib/to-data-table";
import type { VisualizationSpec } from "@microsoft/fabric-visuals";

// Rendered as a DataGrid (row select -> "Place hold"). The bar spec lets validate:visual check the query.
const columnMetadata: ColumnMetadataMap = {
    "trace_genealogy[lot_id]": { name: "lotId", displayName: "Finished lot" },
    "trace_genealogy[facility_id]": { name: "facilityId", displayName: "Facility" },
    "trace_genealogy[sku_id]": { name: "sku", displayName: "SKU" },
    "trace_genealogy[production_date]": { name: "productionDate", displayName: "Produced", format: "yyyy-mm-dd" },
    "trace_genealogy[best_by_date]": { name: "bestBy", displayName: "Best by", format: "yyyy-mm-dd" },
    "[Cases Produced]": { name: "casesProduced", displayName: "Cases produced", format: "#,0" },
    "[Cases Shipped]": { name: "casesShipped", displayName: "Cases shipped", format: "#,0" },
    "[Customers]": { name: "customers", displayName: "Customers", format: "#,0" },
    "[Cases Destroyed]": { name: "casesDestroyed", displayName: "Destroyed (recall)", format: "#,0" },
};

export function traceLotsQuery({ ingredientLotId }: { ingredientLotId: string }) {
    return {
        connection: "ambermoor",
        query: fill(template, { ingredientLotId }),
        columnMetadata,
        vegaLiteSpec: spec as VisualizationSpec,
    };
}
