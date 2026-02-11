/*
 * setup/01_primary_setup.sql
 * Creates database, image repository, and compute pool in primary. 
 * This is one-time setup only needed in the primary before publishing services
 * or setting up replication 
 */

CREATE DATABASE IF NOT EXISTS {{ replicated.database }};
CREATE SCHEMA IF NOT EXISTS {{ replicated.database }}.{{ replicated.schema }};

-- SNOWFLAKE_SSE encryption required for replication
CREATE IMAGE REPOSITORY IF NOT EXISTS {{ replicated.database }}.{{ replicated.schema }}.REPO
    ENCRYPTION = (TYPE = 'SNOWFLAKE_SSE');

CREATE COMPUTE POOL IF NOT EXISTS {{ compute_pool.name }}
    MIN_NODES = {{ compute_pool.min_nodes }}
    MAX_NODES = {{ compute_pool.max_nodes }}
    INSTANCE_FAMILY = {{ compute_pool.instance_family }}
    AUTO_SUSPEND_SECS = {{ compute_pool.auto_suspend_secs }};

-- Verify
SHOW IMAGE REPOSITORIES IN SCHEMA {{ replicated.database }}.{{ replicated.schema }};
SHOW COMPUTE POOLS LIKE '{{ compute_pool.name }}';

/*
 * Next step (do out of band): push your container image to the repository:
 *   snow spcs image-registry login
 *   docker push <repo_url>/<image>:<tag>
 * 
 * Then run: setup/02_primary_failover_group.sql
 */
