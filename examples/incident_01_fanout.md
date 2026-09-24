# Incident: Double-Counted Refunds in Daily Revenue

**Date:** March 3rd
**Impact:** Daily revenue dashboard reported roughly 40% more revenue than the actual figure for 4 hours.

**Description:**
On March 3rd, the `daily_revenue` model was reporting inflated revenue. Investigation showed that the `int_orders_with_refunds` model left-joined the `orders` table to the `refunds` table. Because a single order can have multiple partial refunds, the join fanned out the order rows, duplicating the `order_amount` in the final sum.

**Resolution:**
Fixed the join by aggregating the refunds table to the order level before joining, and added a unique constraint on the intermediate model.
