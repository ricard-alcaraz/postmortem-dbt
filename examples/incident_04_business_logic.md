# Incident: "Shipped" Orders Missing Shipped Date

**Date:** November 5th
**Impact:** Logistics team sent 500 "Where is my order?" emails because the tracking dashboard showed orders as "Shipped" but with no tracking number or date.

**Description:**
On November 5th, a bug in the upstream order management system allowed orders to have their `status` updated to 'shipped' without populating the `shipped_at` timestamp or `tracking_number` columns. 

Our downstream `marts.dim_orders` model simply passes these columns through. The dashboard filters for `status = 'shipped'`, but because `shipped_at` was NULL, the logistics team couldn't pull valid tracking data.

**Resolution:**
1. Immediate: Fixed the upstream bug to enforce `shipped_at` population on status change.
2. Preventative: Need a custom dbt test on `marts.dim_orders` that asserts: IF `status` is 'shipped', THEN `shipped_at` MUST NOT BE NULL.