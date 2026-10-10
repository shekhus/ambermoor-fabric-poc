import query from "./top-waste-skus.dax?raw";
import spec from "./top-waste-skus.json";
import type { ColumnMetadataMap } from "@/lib/to-data-table";
import type { VisualizationSpec } from "@microsoft/fabric-visuals";

const columnMetadata: ColumnMetadataMap = {
    "dim_product[sku_name]": { name: "sku", displayName: "SKU" },
    "fact_waste[reason]": { name: "reason", displayName: "Reason" },
    "[Waste Cases]": { name: "wasteCases", displayName: "Waste Cases", format: "#,0" },
};

export function topWasteSkusQuery() {
    return { connection: "ambermoor", query, columnMetadata, vegaLiteSpec: spec as VisualizationSpec };
}
