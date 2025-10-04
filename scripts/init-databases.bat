@echo off
setlocal EnableDelayedExpansion

:: Set PostgreSQL connection parameters
set PGUSER=design_synapse_user
set PGPASSWORD=design_synapse_password
set PGHOST=localhost
set PGPORT=5432

:: Set PostgreSQL binary path - adjust this based on your PostgreSQL installation
set PGBIN=C:\Program Files\PostgreSQL\16\bin

:: Create databases for each service
for %%d in (user marketplace design project analytics knowledge) do (
    echo Processing database design_synapse_%%d_db...

    :: Check if database exists
    "%PGBIN%\psql" -U %PGUSER% -h %PGHOST% -p %PGPORT% -d postgres -t -c "SELECT 1 FROM pg_database WHERE datname='design_synapse_%%d_db'" | findstr "1" > nul

    IF !ERRORLEVEL! EQU 0 (
        echo Database design_synapse_%%d_db already exists
    ) ELSE (
        echo Creating database design_synapse_%%d_db...
        "%PGBIN%\createdb" -U %PGUSER% -h %PGHOST% -p %PGPORT% design_synapse_%%d_db
        IF !ERRORLEVEL! EQU 0 (
            echo Database design_synapse_%%d_db created successfully

            :: Grant all privileges to the service user
            "%PGBIN%\psql" -U %PGUSER% -h %PGHOST% -p %PGPORT% -d design_synapse_%%d_db -c "GRANT ALL PRIVILEGES ON DATABASE design_synapse_%%d_db TO design_synapse_user;"

            :: Create schema and grant permissions
            "%PGBIN%\psql" -U %PGUSER% -h %PGHOST% -p %PGPORT% -d design_synapse_%%d_db -c "CREATE SCHEMA IF NOT EXISTS design_synapse_%%d; GRANT ALL ON SCHEMA design_synapse_%%d TO design_synapse_user;"
        ) ELSE (
            echo Failed to create database design_synapse_%%d_db
            exit /b 1
        )
    )
)

echo Setting up database access restrictions...
"%PGBIN%\psql" -U %PGUSER% -h %PGHOST% -p %PGPORT% -d postgres -f "%~dp0revoke-cross-access.sql"

echo All databases processed successfully
endlocal
