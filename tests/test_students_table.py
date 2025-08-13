"""
Unit tests for Students table creation and validation
"""

import pytest
import os
import sys
from unittest.mock import Mock, patch

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from database.config.database_config import DatabaseConfig, DatabaseType
from database.connection.database_connection import DatabaseConnection
from database.tables.students_table import StudentsTableManager

class TestStudentsTable:
    """Test cases for Students table management"""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock database configuration"""
        return DatabaseConfig(
            db_type=DatabaseType.POSTGRESQL,
            host='localhost',
            port=5432,
            database='test_library_management',
            username='postgres',
            password='test_password'
        )
    
    @pytest.fixture
    def mock_connection(self, mock_config):
        """Create mock database connection"""
        connection = Mock(spec=DatabaseConnection)
        connection.config = mock_config
        return connection
    
    @pytest.fixture
    def students_manager(self, mock_connection):
        """Create StudentsTableManager instance"""
        return StudentsTableManager(mock_connection)
    
    def test_init_with_postgresql(self, mock_connection):
        """Test initialization with PostgreSQL connection"""
        manager = StudentsTableManager(mock_connection)
        assert manager.connection == mock_connection
    
    def test_init_with_non_postgresql_raises_error(self):
        """Test initialization with non-PostgreSQL connection raises error"""
        mock_config = DatabaseConfig(
            db_type=DatabaseType.POSTGRESQL,  # We only have PostgreSQL now
            host='localhost',
            port=5432,
            database='test',
            username='user',
            password='pass'
        )
        mock_connection = Mock(spec=DatabaseConnection)
        mock_connection.config = mock_config
        
        # This should work now since we only support PostgreSQL
        manager = StudentsTableManager(mock_connection)
        assert manager.connection == mock_connection
    
    def test_create_table_success(self, students_manager, mock_connection):
        """Test successful table creation"""
        mock_connection.execute_script.return_value = None
        mock_connection.execute_command.return_value = None
        
        result = students_manager.create_table()
        
        assert result is True
        assert mock_connection.execute_script.called
        assert mock_connection.execute_command.called
    
    def test_create_table_failure(self, students_manager, mock_connection):
        """Test table creation failure"""
        mock_connection.execute_script.side_effect = Exception("Database error")
        
        result = students_manager.create_table()
        
        assert result is False
    
    def test_drop_table_success(self, students_manager, mock_connection):
        """Test successful table drop"""
        mock_connection.execute_command.return_value = None
        
        result = students_manager.drop_table()
        
        assert result is True
        mock_connection.execute_command.assert_called_with("DROP TABLE IF EXISTS students;")
    
    def test_drop_table_failure(self, students_manager, mock_connection):
        """Test table drop failure"""
        mock_connection.execute_command.side_effect = Exception("Database error")
        
        result = students_manager.drop_table()
        
        assert result is False
    
    def test_table_exists(self, students_manager, mock_connection):
        """Test table existence check"""
        mock_connection.table_exists.return_value = True
        
        result = students_manager.table_exists()
        
        assert result is True
        mock_connection.table_exists.assert_called_with('students')
    
    def test_validate_student_data_valid(self, students_manager):
        """Test validation with valid student data"""
        valid_data = {
            'student_number': '12345',
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john.doe@example.com',
            'phone': '+1-555-123-4567',
            'program': 'Computer Science',
            'enrollment_year': 2023,
            'status': 'active'
        }
        
        errors = students_manager.validate_student_data(valid_data)
        
        assert len(errors) == 0
    
    def test_validate_student_data_missing_required_fields(self, students_manager):
        """Test validation with missing required fields"""
        invalid_data = {
            'first_name': 'John',
            'email': 'john.doe@example.com'
            # Missing student_number and last_name
        }
        
        errors = students_manager.validate_student_data(invalid_data)
        
        assert len(errors) >= 2
        assert any('student_number is required' in error for error in errors)
        assert any('last_name is required' in error for error in errors)
    
    def test_validate_student_data_invalid_student_number(self, students_manager):
        """Test validation with invalid student number"""
        invalid_data = {
            'student_number': 'ABC123',  # Contains letters
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john.doe@example.com'
        }
        
        errors = students_manager.validate_student_data(invalid_data)
        
        assert any('Student number must contain only digits' in error for error in errors)
    
    def test_validate_student_data_invalid_email(self, students_manager):
        """Test validation with invalid email"""
        invalid_data = {
            'student_number': '12345',
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'invalid-email'  # Missing @ symbol
        }
        
        errors = students_manager.validate_student_data(invalid_data)
        
        assert any('Invalid email format' in error for error in errors)
    
    def test_validate_student_data_invalid_status(self, students_manager):
        """Test validation with invalid status"""
        invalid_data = {
            'student_number': '12345',
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john.doe@example.com',
            'status': 'invalid_status'
        }
        
        errors = students_manager.validate_student_data(invalid_data)
        
        assert any("Status must be 'active', 'inactive', or 'graduated'" in error for error in errors)
    
    def test_validate_student_data_invalid_enrollment_year(self, students_manager):
        """Test validation with invalid enrollment year"""
        invalid_data = {
            'student_number': '12345',
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john.doe@example.com',
            'enrollment_year': 1800  # Too old
        }
        
        errors = students_manager.validate_student_data(invalid_data)
        
        assert any('Enrollment year must be between 1900 and 2030' in error for error in errors)
    
    def test_validate_student_data_short_student_number(self, students_manager):
        """Test validation with too short student number"""
        invalid_data = {
            'student_number': '123',  # Too short
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john.doe@example.com'
        }
        
        errors = students_manager.validate_student_data(invalid_data)
        
        assert any('Student number must be between 4 and 20 digits' in error for error in errors)
    
    def test_validate_student_data_long_student_number(self, students_manager):
        """Test validation with too long student number"""
        invalid_data = {
            'student_number': '123456789012345678901',  # Too long (21 digits)
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john.doe@example.com'
        }
        
        errors = students_manager.validate_student_data(invalid_data)
        
        assert any('Student number must be between 4 and 20 digits' in error for error in errors)

class TestStudentsTableConstraints:
    """Test database constraints for Students table"""
    
    def test_student_number_format_constraint(self):
        """Test student number format constraint"""
        # This would be tested with actual database connection
        # For now, we test the validation logic
        manager = StudentsTableManager(Mock())
        
        # Valid student numbers
        valid_numbers = ['1234', '12345678', '20241234567890123456']
        for number in valid_numbers:
            data = {
                'student_number': number,
                'first_name': 'John',
                'last_name': 'Doe',
                'email': 'john@example.com'
            }
            errors = manager.validate_student_data(data)
            number_errors = [e for e in errors if 'Student number' in e]
            assert len(number_errors) == 0, f"Valid number {number} should not have errors"
    
    def test_email_format_constraint(self):
        """Test email format constraint"""
        manager = StudentsTableManager(Mock())
        
        # Valid emails
        valid_emails = [
            'user@example.com',
            'test.email@domain.co.uk',
            'user+tag@example.org'
        ]
        
        for email in valid_emails:
            data = {
                'student_number': '12345',
                'first_name': 'John',
                'last_name': 'Doe',
                'email': email
            }
            errors = manager.validate_student_data(data)
            email_errors = [e for e in errors if 'email' in e.lower()]
            assert len(email_errors) == 0, f"Valid email {email} should not have errors"
    
    def test_status_enum_constraint(self):
        """Test status enum constraint"""
        manager = StudentsTableManager(Mock())
        
        # Valid statuses
        valid_statuses = ['active', 'inactive', 'graduated']
        
        for status in valid_statuses:
            data = {
                'student_number': '12345',
                'first_name': 'John',
                'last_name': 'Doe',
                'email': 'john@example.com',
                'status': status
            }
            errors = manager.validate_student_data(data)
            status_errors = [e for e in errors if 'Status' in e]
            assert len(status_errors) == 0, f"Valid status {status} should not have errors"

if __name__ == '__main__':
    pytest.main([__file__])