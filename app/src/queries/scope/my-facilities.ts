import query from "./my-facilities.dax?raw";
import type { ColumnMetadataMap } from "@/lib/to-data-table";

// The facilities the signed-in user can see. The model's RLS (QA Manager role) trims this to their plant,
// so the app reuses it to scope holds (writeback rows have no RLS of their own yet).
const columnMetadata: ColumnMetadataMap = {
    "dim_facility[facility_id]": { name: "facilityId", displayName: "Facility" },
    "dim_facility[facility_name]": { name: "facilityName", displayName: "Name" },
    "dim_facility[facility_type]": { name: "facilityType", displayName: "Type" },
};

export function myFacilitiesQuery() {
    return { connection: "ambermoor", query, columnMetadata };
}
