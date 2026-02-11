/*
 * setup/03_secondary_failover_group.sql
 * Creates linked failover group in secondary
*/

-- Note: Initial refresh starts automatically after creation
CREATE FAILOVER GROUP IF NOT EXISTS {{ failover_group.name }}
    AS REPLICA OF {{ primary_account }}.{{ failover_group.name }};

-- Verify failover group
SHOW FAILOVER GROUPS;

-- Verify replicated database is visible
SHOW DATABASES IN FAILOVER GROUP {{ failover_group.name }};

/*
 * Wait for the database to appear in SHOW DATABASES before proceeding.
 * 
 * Once replication is complete, deploy the service:
 *   python deploy.py service primary
 *   python deploy.py service secondary
 */
