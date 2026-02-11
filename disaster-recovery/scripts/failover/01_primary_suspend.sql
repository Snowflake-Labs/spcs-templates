/*
 * failover/01_primary_suspend.sql
 * Suspends primary compute pool during failover. Best effort - may fail 
 * if primary account is unreachable.
 */

ALTER COMPUTE POOL {{ compute_pool.name }} SUSPEND;

-- Verify
SHOW COMPUTE POOLS LIKE '{{ compute_pool.name }}';
