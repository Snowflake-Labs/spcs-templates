-- The following SQL instructions will set up a table for the third endpoint of the examples to query.
-- Make sure to create the service(s) attached to the schema below, and use the same role
-- to create the table and the service.

create database if not exists stocks_db;
use database stocks_db;

create schema if not exists stocks_schema;
use schema stocks_schema;

create table if not exists stocks_db.stocks_schema.stock_exchanges (
symbol STRING,
exchange STRING
);

insert into stock_exchanges (symbol, exchange)
select 'AAPL', 'NYSE'
where not exists (select 1 from stock_exchanges);

create or replace procedure get_stock_exchange(symbol string)
returns string
language python
runtime_version = '3.9'
packages = ('snowflake-snowpark-python', 'snowflake-telemetry-python')
handler = 'get_stock_exchange'
as
$$
import logging
def get_stock_exchange(session, symbol):
    logging.info("running simple query")
    return session.sql(f"select exchange from stock_exchanges where symbol = '{symbol}'").collect()
$$;

