import query from "./supplier-notices.dax?raw";
import type { ColumnMetadataMap } from "@/lib/to-data-table";

const columnMetadata: ColumnMetadataMap = {
    "fact_supplier_notice[notice_id]": { name: "noticeId", displayName: "Notice" },
    "fact_supplier_notice[ingredient_lot_id]": { name: "ingredientLotId", displayName: "Ingredient lot" },
    "fact_supplier_notice[notice_date]": { name: "noticeDate", displayName: "Date", format: "yyyy-mm-dd" },
    "fact_supplier_notice[notice_type]": { name: "noticeType", displayName: "Type" },
    "fact_supplier_notice[status]": { name: "status", displayName: "Status" },
};

export function supplierNoticesQuery() {
    return { connection: "ambermoor", query, columnMetadata };
}
