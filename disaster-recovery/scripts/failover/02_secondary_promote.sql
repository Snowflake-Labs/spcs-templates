/*
 * failover/02_secondary_promote.sql
 * Promotes secondary to primary during a failover event
 */

-- This makes the secondary the new primary, allowing writes to replicated DB
ALTER FAILOVER GROUP {{ failover_group.name }} PRIMARY;

-- Verify promotion
SHOW FAILOVER GROUPS;

-- Resume compute pool 
ALTER COMPUTE POOL {{ compute_pool.name }} RESUME;

-- Wait for compute pool to be ready
SHOW COMPUTE POOLS LIKE '{{ compute_pool.name }}';

-- Resume service
ALTER SERVICE {{ local.database }}.{{ local.schema }}.{{ service.name }} RESUME;

-- Verify service is starting
SELECT SYSTEM$GET_SERVICE_STATUS('{{ local.database }}.{{ local.schema }}.{{ service.name }}');

-- Get the public ingress URL (this is now the active endpoint)
SHOW ENDPOINTS IN SERVICE {{ local.database }}.{{ local.schema }}.{{ service.name }};
