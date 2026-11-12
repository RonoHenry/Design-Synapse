#!/bin/bash
# DEPRECATED: This script was used for PostgreSQL setup.
# The project now uses TiDB Serverless, which does not require local database initialization.
#
# To set up databases on TiDB Serverless:
# 1. Log in to your TiDB Cloud console
# 2. Connect to your TiDB cluster using the MySQL client or TiDB Cloud SQL Editor
# 3. Run the following SQL commands:
#
# CREATE DATABASE IF NOT EXISTS design_synapse_user_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
# CREATE DATABASE IF NOT EXISTS design_synapse_project_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
# CREATE DATABASE IF NOT EXISTS design_synapse_knowledge_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
# CREATE DATABASE IF NOT EXISTS design_synapse_marketplace_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
# CREATE DATABASE IF NOT EXISTS design_synapse_design_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
# CREATE DATABASE IF NOT EXISTS design_synapse_analytics_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
#
# 4. Run Alembic migrations for each service:
#    cd apps/user-service && alembic upgrade head
#    cd apps/project-service && alembic upgrade head
#    cd apps/knowledge-service && alembic upgrade head
#
# Note: TiDB Serverless handles user management and permissions through the cloud console.
# Service-specific users are not required as all services use the same TiDB cluster credentials.

echo "This script is deprecated. Please use TiDB Serverless for database setup."
echo "See the comments in this file for instructions."
exit 1
