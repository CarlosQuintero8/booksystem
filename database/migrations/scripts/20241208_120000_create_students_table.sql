-- Description: Create Students table with validation constraints
-- Version: 20241208_120000
-- Created: 2024-12-08T12:00:00

-- UP
-- Create Students table with comprehensive validation constraints

-- PostgreSQL version
CREATE TABLE IF NOT EXISTS students (
    student_id SERIAL PRIMARY KEY,
    student_number VARCHAR(20) UNIQUE NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(20),
    program VARCHAR(100),
    enrollment_year INTEGER,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'graduated')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT chk_student_number_format CHECK (student_number ~ '^[0-9]{4,20}$'),
    CONSTRAINT chk_email_format CHECK (email ~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'),
    CONSTRAINT chk_phone_format CHECK (phone IS NULL OR phone ~ '^[\+]?[0-9\-\s\(\)]{7,20}$'),
    CONSTRAINT chk_enrollment_year CHECK (enrollment_year IS NULL OR (enrollment_year >= 1900 AND enrollment_year <= EXTRACT(YEAR FROM CURRENT_DATE) + 1)),
    CONSTRAINT chk_names_not_empty CHECK (LENGTH(TRIM(first_name)) > 0 AND LENGTH(TRIM(last_name)) > 0)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_students_student_number ON students(student_number);
CREATE INDEX IF NOT EXISTS idx_students_email ON students(student_number);
CREATE INDEX IF NOT EXISTS idx_students_status ON students(status);
CREATE INDEX IF NOT EXISTS idx_students_program ON students(program);
CREATE INDEX IF NOT EXISTS idx_students_name ON students(last_name, first_name);

-- Create trigger for updating updated_at timestamp
CREATE OR REPLACE FUNCTION update_students_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_students_updated_at
    BEFORE UPDATE ON students
    FOR EACH ROW
    EXECUTE FUNCTION update_students_updated_at();

-- Create audit trigger for students table
CREATE TRIGGER trigger_students_audit
    AFTER INSERT OR UPDATE OR DELETE ON students
    FOR EACH ROW
    EXECUTE FUNCTION audit_trigger_function();

-- Add comments for documentation
COMMENT ON TABLE students IS 'Student information and enrollment details';
COMMENT ON COLUMN students.student_id IS 'Primary key, auto-incrementing student ID';
COMMENT ON COLUMN students.student_number IS 'Unique student identification number';
COMMENT ON COLUMN students.first_name IS 'Student first name';
COMMENT ON COLUMN students.last_name IS 'Student last name';
COMMENT ON COLUMN students.email IS 'Student email address (unique)';
COMMENT ON COLUMN students.phone IS 'Student phone number (optional)';
COMMENT ON COLUMN students.program IS 'Academic program or major';
COMMENT ON COLUMN students.enrollment_year IS 'Year of enrollment';
COMMENT ON COLUMN students.status IS 'Student status: active, inactive, or graduated';

-- DOWN
-- Remove audit trigger
DROP TRIGGER IF EXISTS trigger_students_audit ON students;

-- Remove update trigger and function
DROP TRIGGER IF EXISTS trigger_students_updated_at ON students;
DROP FUNCTION IF EXISTS update_students_updated_at();

-- Remove indexes
DROP INDEX IF EXISTS idx_students_name;
DROP INDEX IF EXISTS idx_students_program;
DROP INDEX IF EXISTS idx_students_status;
DROP INDEX IF EXISTS idx_students_email;
DROP INDEX IF EXISTS idx_students_student_number;

-- Drop table
DROP TABLE IF EXISTS students;