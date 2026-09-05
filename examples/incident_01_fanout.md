# Incident: Double-Counted Refunds in Daily Revenue

**Date:** March 3rd
**Impact:** Daily revenue dashboard reported 2x the actual revenue for 4 hours.

**Description:**
On March 3rd, the `daily_revenue` model was reporting double the actual revenue. Investigation showed that the `orders` table was left-joined to the `refunds` table in the revenue calculation. Because a single order can have multiple partial refunds, the join fanned out the order rows, duplicating the `order_amount` in the final sum. 

**Resolution:**
Fixed the join by aggregating the refunds table to the order level before joining, and added a unique constraint on the intermediate model.