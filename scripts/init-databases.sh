#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Create service-specific roles
    CREATE ROLE design_synapse_analytics LOGIN PASSWORD 'analytics_password';
    CREATE ROLE design_synapse_design LOGIN PASSWORD 'design_password';
    CREATE ROLE design_synapse_marketplace LOGIN PASSWORD 'marketplace_password';
    CREATE ROLE design_synapse_project LOGIN PASSWORD 'project_password';
    CREATE ROLE design_synapse_user LOGIN PASSWORD 'user_password';

    -- Create databases
    CREATE DATABASE design_synapse_user_db;
    CREATE DATABASE design_synapse_marketplace_db;
    CREATE DATABASE design_synapse_design_db;
    CREATE DATABASE design_synapse_project_db;
    CREATE DATABASE design_synapse_analytics_db;

    -- Grant connect privileges only to specific roles for their databases
    GRANT CONNECT ON DATABASE design_synapse_user_db TO design_synapse_user;
    GRANT CONNECT ON DATABASE design_synapse_marketplace_db TO design_synapse_marketplace;
    GRANT CONNECT ON DATABASE design_synapse_design_db TO design_synapse_design;
    GRANT CONNECT ON DATABASE design_synapse_project_db TO design_synapse_project;
    GRANT CONNECT ON DATABASE design_synapse_analytics_db TO design_synapse_analytics;

    -- Revoke public access
    REVOKE CONNECT ON DATABASE design_synapse_user_db FROM PUBLIC;
    REVOKE CONNECT ON DATABASE design_synapse_marketplace_db FROM PUBLIC;
    REVOKE CONNECT ON DATABASE design_synapse_design_db FROM PUBLIC;
    REVOKE CONNECT ON DATABASE design_synapse_project_db FROM PUBLIC;
    REVOKE CONNECT ON DATABASE design_synapse_analytics_db FROM PUBLIC;
EOSQL

# Connect to each database and set up schema permissions
for db in user marketplace design project analytics; do
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "design_synapse_${db}_db" <<-EOSQL
        REVOKE ALL ON ALL TABLES IN SCHEMA public FROM PUBLIC;
        REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM PUBLIC;
        REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM PUBLIC;
        
        GRANT ALL ON ALL TABLES IN SCHEMA public TO design_synapse_${db};
        GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO design_synapse_${db};
        GRANT ALL ON ALL FUNCTIONS IN SCHEMA public TO design_synapse_${db};
        
        ALTER DEFAULT PRIVILEGES IN SCHEMA public 
        GRANT ALL ON TABLES TO design_synapse_${db};
        
        ALTER DEFAULT PRIVILEGES IN SCHEMA public 
        GRANT ALL ON SEQUENCES TO design_synapse_${db};
        
        ALTER DEFAULT PRIVILEGES IN SCHEMA public 
        GRANT ALL ON FUNCTIONS TO design_synapse_${db};
EOSQL
done