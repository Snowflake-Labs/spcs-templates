/*
 * setup/02_primary_failover_group.sql
 * One-time failover group setup in the primary only
 */

CREATE FAILOVER GROUP IF NOT EXISTS {{ failover_group.name }}
    OBJECT_TYPES = DATABASES, COMPUTE POOLS
    ALLOWED_DATABASES = {{ replicated.database }}
    -- NOTE: EXTERNAL ACCESS INTEGRATIONS intentionally excluded
    -- Primary and secondary maintain their own EAIs with distinct endpoints
    ALLOWED_ACCOUNTS = {{ secondary_account }}
    REPLICATION_SCHEDULE = '{{ failover_group.replication_schedule }}';

-- Verify
SHOW FAILOVER GROUPS;

/*
 * Next step: Run in secondary:
 *   setup/03_secondary_failover_group.sql
 */
