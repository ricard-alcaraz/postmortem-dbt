# Incident: NULL Full Names in Customer Dashboard

**Date:** October 12th
**Impact:** Approximately 15% of newly onboarded customers appeared with a "NULL" full name in the CRM and BI dashboards, causing confusion for the sales team.

**Description:**
On October 12th, a new batch of customer data was ingested from the upstream CRM. Several of these new records had missing `first_name` values (they were NULL), but valid `last_name` and `email` values. 

Investigation revealed that the `marts.dim_customers` model calculates the `full_name` column using simple string concatenation: `first_name || ' ' || last_name`. In our data warehouse, concatenating any string with a NULL value results in a NULL output. Therefore, any customer missing a first name ended up with a NULL `full_name`, rather than just displaying their last name.

**Resolution:**
1. Immediate: Updated the `dim_customers.sql` model to use `COALESCE(first_name, '') || ' ' || COALESCE(last_name, '')` to safely handle missing names.
2. Preventative: Need to add a dbt test to ensure `full_name` is never NULL in the final marts layer, and ideally catch nulls in `first_name` or `last_name` at the staging layer.