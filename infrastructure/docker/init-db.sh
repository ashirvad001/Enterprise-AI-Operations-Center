#!/bin/bash
set -e

# This script runs automatically when the PostgreSQL container is first created.
# It sets up the required extensions and schemas.

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Enable extensions in the public schema
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    CREATE EXTENSION IF NOT EXISTS "vector";      -- For pgvector (RAG)
    CREATE EXTENSION IF NOT EXISTS "pgcrypto";    -- For cryptographic functions

    -- Create schemas for the different microservices
    CREATE SCHEMA IF NOT EXISTS auth;
    CREATE SCHEMA IF NOT EXISTS rbac;
    CREATE SCHEMA IF NOT EXISTS agent;
    CREATE SCHEMA IF NOT EXISTS rag;
    CREATE SCHEMA IF NOT EXISTS audit;
    CREATE SCHEMA IF NOT EXISTS mlops;
    CREATE SCHEMA IF NOT EXISTS edge;
    
    -- Grant usage on schemas
    GRANT ALL ON SCHEMA auth TO "$POSTGRES_USER";
    GRANT ALL ON SCHEMA rbac TO "$POSTGRES_USER";
    GRANT ALL ON SCHEMA agent TO "$POSTGRES_USER";
    GRANT ALL ON SCHEMA rag TO "$POSTGRES_USER";
    GRANT ALL ON SCHEMA audit TO "$POSTGRES_USER";
    GRANT ALL ON SCHEMA mlops TO "$POSTGRES_USER";
    GRANT ALL ON SCHEMA edge TO "$POSTGRES_USER";

    -- Notice
    \echo 'Database schemas and extensions initialized successfully.'
EOSQL
