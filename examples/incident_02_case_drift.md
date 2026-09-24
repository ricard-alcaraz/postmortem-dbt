# Incident: Delivered Orders Missing From the Fulfillment Dashboard

**Date:** May 14th
**Impact:** About 9% of that day's delivered orders were missing from the fulfillment dashboard for 6 hours, and the post-delivery survey emails for those orders were never sent.

**Description:**
On May 14th, a release of the upstream order management system started writing the `status` value `Delivered` (capitalized) instead of `delivered` for orders confirmed through the mobile app. Our `marts.dim_orders` model passes `status` through unchanged, and both the fulfillment dashboard and the survey trigger filter on `status = 'delivered'`. The affected orders were silently dropped instead of raising an error.

The column is supposed to contain only five values: `pending`, `shipped`, `delivered`, `cancelled` and `returned`. Nothing in our pipeline checked that.

**Resolution:**
1. Immediate: The upstream team reverted the release and backfilled the affected rows with the lowercase value.
2. Preventative: Add a dbt test on `marts.dim_orders` so any status outside the five expected values fails the run instead of disappearing from the dashboards.
