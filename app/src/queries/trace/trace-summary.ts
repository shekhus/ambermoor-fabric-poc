import template from "./trace-summary.dax?raw";
import { fill } from "./dax-param";
import type { ColumnMetadataMap } from "@/lib/to-data-table";

const columnMetadata: ColumnMetadataMap = {
    "[Finished Lots]": { name: "lots", displayName: "Finished lots", format: "#,0" },
    "[Cases Shipped]": { name: "casesShipped", displayName: "Cases shipped", format: "#,0" },
    "[Customers]": { name: "customers", displayName: "Customers", format: "#,0" },
    "[Shipments]": { name: "shipments", displayName: "Shipments", format: "#,0" },
    "[Cases Destroyed]": { name: "casesDestroyed", displayName: "Cases destroyed (recall)", format: "#,0" },
};

export function traceSummaryQuery({ ingredientLotId }: { ingredientLotId: string }) {
    return { connection: "ambermoor", query: fill(template, { ingredientLotId }), columnMetadata };
}
