# 2: Create a service

The `make` command in the preceding section also creates a service specification file (`metrics-service.yml`) in the user-metrics directory. When you execute a `CREATE SERVICE` statement to create the service, you can include the contents of this file inline in that statement.

1. To create the service, execute the following `CREATE SERVICE` command using SnowSQL CLI or Snowsight web interface. Make sure you use the `test_role` to execute the `CREATE SERVICE` command.

```sql
    CREATE SERVICE metrics_visualizer
      IN COMPUTE POOL tutorial_compute_pool
      FROM SPECIFICATION $$
        <copy/paste the specification from metrics-service.yml file>
      $$;
    ```

2. Run `SHOW SERVICE CONTAINERS IN SERVICE` statement to verify that all of the service containers are running.

    ```sql
    SHOW SERVICE CONTAINERS IN SERVICE metrics_visualizer;
    ```
