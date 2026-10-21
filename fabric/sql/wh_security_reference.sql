/* WH_FreshyFresh: security reference for lab L5                                     [D1]
   REFERENCE SOLUTION. Try the lab first; use this to check your work.

   Assumes lab L4 created dbo.dim_facility, dbo.dim_customer, dbo.fact_shipment in WH_FreshyFresh (CTAS from the
   lakehouse gold layer, same column names as docs/data-model.md).
   Replace the UPNs with your two test users. Test as those users (Viewer + warehouse Read), not as yourself.
   Verify on Learn: which workspace roles bypass RLS/CLS/DDM in a Fabric Warehouse; supported data types (VARCHAR).

   Databricks analogue: Unity Catalog row filters + column masks.
*/

-- 1) Row-level security: QA managers see only their facility; '*' grants all facilities ----------------------
CREATE SCHEMA sec;
GO

CREATE TABLE sec.user_facility
(
    upn         VARCHAR(256) NOT NULL,
    facility_id VARCHAR(8)   NOT NULL      -- '*' = all facilities
);
GO

INSERT INTO sec.user_facility (upn, facility_id) VALUES
    ('qa.p03@yourtenant.onmicrosoft.com', 'P03'),
    ('ops.director@yourtenant.onmicrosoft.com', '*');
GO

CREATE FUNCTION sec.fn_facility_filter(@facility_id AS VARCHAR(8))
    RETURNS TABLE
WITH SCHEMABINDING
AS
    RETURN
        SELECT 1 AS allowed
        FROM sec.user_facility AS u
        WHERE u.upn = USER_NAME()
          AND (u.facility_id = @facility_id OR u.facility_id = '*');
GO

CREATE SECURITY POLICY sec.FacilityFilter
    ADD FILTER PREDICATE sec.fn_facility_filter(ship_from_facility_id) ON dbo.fact_shipment,
    ADD FILTER PREDICATE sec.fn_facility_filter(facility_id) ON dbo.dim_facility
WITH (STATE = ON);
GO

-- Test (as qa.p03): expect only P03 rows
-- SELECT ship_from_facility_id, COUNT(*) AS shipments FROM dbo.fact_shipment GROUP BY ship_from_facility_id;

-- 2) Column-level security: QA managers can't read customer contact or credit columns ---------------------------
GRANT SELECT ON dbo.dim_customer (customer_id, customer_name, channel, ship_from_facility_id, country, region)
    TO [qa.p03@yourtenant.onmicrosoft.com];
GO
-- Test (as qa.p03): SELECT contact_email FROM dbo.dim_customer;  -> permission error

-- 3) Dynamic data masking: obfuscates for non-privileged readers. NOT a security boundary (exam favourite)
ALTER TABLE dbo.dim_customer ALTER COLUMN contact_email ADD MASKED WITH (FUNCTION = 'email()');
ALTER TABLE dbo.dim_customer ALTER COLUMN contact_phone ADD MASKED WITH (FUNCTION = 'partial(0,"XXX-XX",2)');
ALTER TABLE dbo.dim_customer ALTER COLUMN credit_limit_usd ADD MASKED WITH (FUNCTION = 'default()');
GO
GRANT UNMASK TO [ops.director@yourtenant.onmicrosoft.com];
GO

-- Clean-up helpers (run only when re-doing the lab)
-- DROP SECURITY POLICY sec.FacilityFilter;  DROP FUNCTION sec.fn_facility_filter;  DROP TABLE sec.user_facility;
