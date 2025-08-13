-- PostgreSQL initialization script for Library Management System
-- This script creates the database and initial setup for PostgreSQL

-- Create database (run this separately as superuser)
-- CREATE DATABASE library_management;
-- CREATE USER library_user WITH PASSWORD 'your_password_here';
-- GRANT ALL PRIVILEGES ON DATABASE library_management TO library_user;

-- Connect to library_management database before running the rest

-- Enable UUID extension for potential future use
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create custom types for enums
DO $$ BEGIN
    CREATE TYPE student_status AS ENUM ('active', 'inactive', 'graduated');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE book_type AS ENUM ('physical', 'digital');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE book_status AS ENUM ('available', 'loaned', 'maintenance', 'lost');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE loan_status AS ENUM ('active', 'returned', 'overdue', 'lost');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Set timezone
SET timezone = 'UTC';

-- Create schema for library management
CREATE SCHEMA IF NOT EXISTS library;

-- Set search path
SET search_path TO library, public;

-- Grant permissions to library_user
GRANT USAGE ON SCHEMA library TO library_user;
GRANT CREATE ON SCHEMA library TO library_user;

-- Create sequences for auto-increment IDs
CREATE SEQUENCE IF NOT EXISTS student_id_seq;
CREATE SEQUENCE IF NOT EXISTS shelf_id_seq;
CREATE SEQUENCE IF NOT EXISTS book_id_seq;
CREATE SEQUENCE IF NOT EXISTS loan_id_seq;
CREATE SEQUENCE IF NOT EXISTS category_id_seq;

-- Grant sequence permissions
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA library TO library_user;

-- Create function to update timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create function for checking email format
CREATE OR REPLACE FUNCTION is_valid_email(email TEXT)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$';
END;
$$ LANGUAGE plpgsql;

-- Create function for checking ISBN format
CREATE OR REPLACE FUNCTION is_valid_isbn(isbn TEXT)
RETURNS BOOLEAN AS $$
BEGIN
    -- Check for ISBN-10 or ISBN-13 format
    RETURN isbn ~ '^(?:ISBN(?:-1[03])?:? )?(?=[0-9X]{10}$|(?=(?:[0-9]+[- ]){3})[- 0-9X]{13}$|97[89][0-9]{10}$|(?=(?:[0-9]+[- ]){4})[- 0-9]{17}$)(?:97[89][- ]?)?[0-9]{1,5}[- ]?[0-9]+[- ]?[0-9]+[- ]?[0-9X]$';
END;
$$ LANGUAGE plpgsql;

-- Create logging table for audit trail
CREATE TABLE IF NOT EXISTS audit_log (
    log_id SERIAL PRIMARY KEY,
    table_name VARCHAR(50) NOT NULL,
    operation VARCHAR(10) NOT NULL,
    old_values JSONB,
    new_values JSONB,
    user_id VARCHAR(50),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create audit trigger function
CREATE OR REPLACE FUNCTION audit_trigger_function()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        INSERT INTO audit_log (table_name, operation, old_values, timestamp)
        VALUES (TG_TABLE_NAME, TG_OP, row_to_json(OLD), CURRENT_TIMESTAMP);
        RETURN OLD;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO audit_log (table_name, operation, old_values, new_values, timestamp)
        VALUES (TG_TABLE_NAME, TG_OP, row_to_json(OLD), row_to_json(NEW), CURRENT_TIMESTAMP);
        RETURN NEW;
    ELSIF TG_OP = 'INSERT' THEN
        INSERT INTO audit_log (table_name, operation, new_values, timestamp)
        VALUES (TG_TABLE_NAME, TG_OP, row_to_json(NEW), CURRENT_TIMESTAMP);
        RETURN NEW;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions on functions and tables
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA library TO library_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA library TO library_user;

COMMENT ON SCHEMA library IS 'Library Management System schema';
COMMENT ON FUNCTION update_updated_at_column() IS 'Automatically updates updated_at timestamp';
COMMENT ON FUNCTION is_valid_email(TEXT) IS 'Validates email format using regex';
COMMENT ON FUNCTION is_valid_isbn(TEXT) IS 'Validates ISBN-10 and ISBN-13 formats';
COMMENT ON TABLE audit_log IS 'Audit trail for all database changes';