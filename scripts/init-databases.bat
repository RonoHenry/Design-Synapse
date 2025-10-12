@echo off
REM DEPRECATED: This script was used for PostgreSQL setup.
REM The project now uses TiDB Serverless, which does not require local database initialization.
REM
REM To set up databases on TiDB Serverless:
REM 1. Log in to your TiDB Cloud console
REM 2. Connect to your TiDB cluster using the MySQL client or TiDB Cloud SQL Editor
REM 3. Run the following SQL commands:
REM
REM CREATE DATABASE IF NOT EXISTS design_synapse_user_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
REM CREATE DATABASE IF NOT EXISTS design_synapse_project_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
REM CREATE DATABASE IF NOT EXISTS design_synapse_knowledge_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
REM CREATE DATABASE IF NOT EXISTS design_synapse_marketplace_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
REM CREATE DATABASE IF NOT EXISTS design_synapse_design_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
REM CREATE DATABASE IF NOT EXISTS design_synapse_analytics_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
REM
REM 4. Run Alembic migrations for each service:
REM    cd apps\user-service && alembic upgrade head
REM    cd apps\project-service && alembic upgrade head
REM    cd apps\knowledge-service && alembic upgrade head
REM
REM Note: TiDB Serverless handles user management and permissions through the cloud console.
REM Service-specific users are not required as all services use the same TiDB cluster credentials.

echo This script is deprecated. Please use TiDB Serverless for database setup.
echo See the comments in this file for instructions.
exit /b 1
