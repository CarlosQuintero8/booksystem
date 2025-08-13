"""
Students table creation and management for PostgreSQL
"""

from database.config.database_config import DatabaseType
from database.connection.database_connection import DatabaseConnection

class StudentsTableManager:
    """Manages Students table creation and operations for PostgreSQL"""
    
    def __init__(self, connection: DatabaseConnection):
        self.connection = connection
        if connection.config.db_type != DatabaseType.POSTGRESQL:
            raise ValueError("StudentsTableManager only supports PostgreSQL")
    
    def create_table(self) -> bool:
        """Create Students table with PostgreSQL-specific constraints"""
        
        try:
            return self._create_postgresql_table()
        except Exception as e:
            print(f"Error creating Students table: {e}")
            return False
    
    def _create_postgresql_table(self) -> bool:
        """Create Students table for PostgreSQL"""
        
        sql = """
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
            CONSTRAINT chk_email_format CHECK (email ~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$'),
            CONSTRAINT chk_phone_format CHECK (phone IS NULL OR phone ~ '^[\\+]?[0-9\\-\\s\\(\\)]{7,20}$'),
            CONSTRAINT chk_enrollment_year CHECK (enrollment_year IS NULL OR (enrollment_year >= 1900 AND enrollment_year <= EXTRACT(YEAR FROM CURRENT_DATE) + 1)),
            CONSTRAINT chk_names_not_empty CHECK (LENGTH(TRIM(first_name)) > 0 AND LENGTH(TRIM(last_name)) > 0)
        );
        """
        
        self.connection.execute_script(sql)
        self._create_postgresql_indexes()
        self._create_postgresql_triggers()
        return True
    

    
    def _create_postgresql_indexes(self):
        """Create indexes for PostgreSQL"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_students_student_number ON students(student_number);",
            "CREATE INDEX IF NOT EXISTS idx_students_email ON students(email);",
            "CREATE INDEX IF NOT EXISTS idx_students_status ON students(status);",
            "CREATE INDEX IF NOT EXISTS idx_students_program ON students(program);",
            "CREATE INDEX IF NOT EXISTS idx_students_name ON students(last_name, first_name);",
            "CREATE INDEX IF NOT EXISTS idx_students_enrollment_year ON students(enrollment_year);"
        ]
        
        for index_sql in indexes:
            self.connection.execute_command(index_sql)
    

    
    def _create_postgresql_triggers(self):
        """Create triggers for PostgreSQL"""
        # Update timestamp trigger
        trigger_function = """
        CREATE OR REPLACE FUNCTION update_students_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
        
        trigger = """
        CREATE TRIGGER trigger_students_updated_at
            BEFORE UPDATE ON students
            FOR EACH ROW
            EXECUTE FUNCTION update_students_updated_at();
        """
        
        self.connection.execute_script(trigger_function)
        self.connection.execute_command(trigger)
    

    
    def drop_table(self) -> bool:
        """Drop Students table"""
        try:
            self.connection.execute_command("DROP TABLE IF EXISTS students;")
            return True
        except Exception as e:
            print(f"Error dropping Students table: {e}")
            return False
    
    def table_exists(self) -> bool:
        """Check if Students table exists"""
        return self.connection.table_exists('students')
    
    def validate_student_data(self, student_data: dict) -> list:
        """Validate student data before insertion"""
        errors = []
        
        # Required fields
        required_fields = ['student_number', 'first_name', 'last_name', 'email']
        for field in required_fields:
            if not student_data.get(field):
                errors.append(f"{field} is required")
        
        # Student number format
        student_number = student_data.get('student_number', '')
        if student_number and not student_number.isdigit():
            errors.append("Student number must contain only digits")
        if len(student_number) < 4 or len(student_number) > 20:
            errors.append("Student number must be between 4 and 20 digits")
        
        # Email format (basic validation)
        email = student_data.get('email', '')
        if email and '@' not in email:
            errors.append("Invalid email format")
        
        # Status validation
        status = student_data.get('status', 'active')
        if status not in ['active', 'inactive', 'graduated']:
            errors.append("Status must be 'active', 'inactive', or 'graduated'")
        
        # Enrollment year validation
        enrollment_year = student_data.get('enrollment_year')
        if enrollment_year:
            try:
                year = int(enrollment_year)
                if year < 1900 or year > 2030:
                    errors.append("Enrollment year must be between 1900 and 2030")
            except (ValueError, TypeError):
                errors.append("Enrollment year must be a valid integer")
        
        return errors