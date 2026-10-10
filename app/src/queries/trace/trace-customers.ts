import template from "./trace-customers.dax?raw";
import spec from "./trace-customers.json";
import { fill } from "./dax-param";
import type { ColumnMetadataMap } from "@/lib/to-data-table";
import type { VisualizationSpec } from "@microsoft/fabric-visuals";

const columnMetadata: ColumnMetadataMap = {
    "dim_customer[customer_name]": { name: "customer", displayName: "Customer" },
    "dim_customer[channel]": { name: "channel", displayName: "Channel" },
    "[Cases Shipped]": { name: "casesShipped", displayName: "Cases shipped", format: "#,0" },
    "[Shipments]": { name: "shipments", displayName: "Shipments", format: "#,0" },
};

export function traceCustomersQuery({ ingredientLotId }: { ingredientLotId: string }) {
    return {
        connection: "ambermoor",
        query: fill(template, { ingredientLotId }),
        columnMetadata,
        vegaLiteSpec: spec as VisualizationSpec,
    };
}
