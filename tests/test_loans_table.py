"""
Unit tests for Loans table creation and validation
"""

import pytest
import os
import sys
from datetime import date, datetime, timedelta
from unittest.mock import Mock, patch

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from database.config.database_config import DatabaseConfig, DatabaseType
from database.connection.database_connection import DatabaseConnection
from database.tables.loans_table import LoansTableManager


class TestLoansTable:
    """Test cases for Loans table management"""
    
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
    def loans_manager(self, mock_connection):
        """Create LoansTableManager instance"""
        return LoansTableManager(mock_connection)
    
    def test_init_with_postgresql(self, mock_connection):
        """Test initialization with PostgreSQL connection"""
        manager = LoansTableManager(mock_connection)
        assert manager.connection == mock_connection
    
    def test_create_table_success(self, loans_manager, mock_connection):
        """Test successful table creation"""
        mock_connection.execute_script.return_value = None
        mock_connection.execute_command.return_value = None
        
        result = loans_manager.create_table()
        
        assert result is True
        assert mock_connection.execute_script.called
        assert mock_connection.execute_command.called
    
    def test_create_table_failure(self, loans_manager, mock_connection):
        """Test table creation failure"""
        mock_connection.execute_script.side_effect = Exception("Database error")
        
        result = loans_manager.create_table()
        
        assert result is False
    
    def test_drop_table_success(self, loans_manager, mock_connection):
        """Test successful table drop"""
        mock_connection.execute_command.return_value = None
        
        result = loans_manager.drop_table()
        
        assert result is True
        # Should drop views, functions, and table
        assert mock_connection.execute_command.call_count >= 7
    
    def test_drop_table_failure(self, loans_manager, mock_connection):
        """Test table drop failure"""
        mock_connection.execute_command.side_effect = Exception("Database error")
        
        result = loans_manager.drop_table()
        
        assert result is False
    
    def test_table_exists(self, loans_manager, mock_connection):
        """Test table existence check"""
        mock_connection.table_exists.return_value = True
        
        result = loans_manager.table_exists()
        
        assert result is True
        mock_connection.table_exists.assert_called_with('loans')
    
    def test_validate_loan_data_valid(self, loans_manager):
        """Test validation with valid loan data"""
        today = date.today()
        return_date = today + timedelta(days=14)
        
        valid_data = {
            'book_id': 1,
            'student_id': 1,
            'loan_date': today,
            'estimated_return_date': return_date,
            'loan_status': 'active',
            'renewal_count': 0,
            'notes': 'Test loan'
        }
        
        errors = loans_manager.validate_loan_data(valid_data)
        
        assert len(errors) == 0
    
    def test_validate_loan_data_missing_required_fields(self, loans_manager):
        """Test validation with missing required fields"""
        invalid_data = {
            'loan_date': date.today(),
            'notes': 'Test loan'
            # Missing book_id and student_id
        }
        
        errors = loans_manager.validate_loan_data(invalid_data)
        
        assert len(errors) >= 2
        assert any('book_id is required' in error for error in errors)
        assert any('student_id is required' in error for error in errors)
    
    def test_validate_loan_data_future_loan_date(self, loans_manager):
        """Test validation with future loan date"""
        future_date = date.today() + timedelta(days=1)
        
        invalid_data = {
            'book_id': 1,
            'student_id': 1,
            'loan_date': future_date
        }
        
        errors = loans_manager.validate_loan_data(invalid_data)
        
        assert any('Loan date cannot be in the future' in error for error in errors)
    
    def test_validate_loan_data_invalid_return_date(self, loans_manager):
        """Test validation with invalid return date"""
        today = date.today()
        yesterday = today - timedelta(days=1)
        
        invalid_data = {
            'book_id': 1,
            'student_id': 1,
            'loan_date': today,
            'estimated_return_date': yesterday  # Before loan date
        }
        
        errors = loans_manager.validate_loan_data(invalid_data)
        
        assert any('Estimated return date must be after loan date' in error for error in errors)
    
    def test_validate_loan_data_excessive_loan_period(self, loans_manager):
        """Test validation with excessive loan period"""
        today = date.today()
        far_future = today + timedelta(days=400)  # More than 365 days
        
        invalid_data = {
            'book_id': 1,
            'student_id': 1,
            'loan_date': today,
            'estimated_return_date': far_future
        }
        
        errors = loans_manager.validate_loan_data(invalid_data)
        
        assert any('Loan period cannot exceed 365 days' in error for error in errors)
    
    def test_validate_loan_data_invalid_actual_return_date(self, loans_manager):
        """Test validation with invalid actual return date"""
        today = date.today()
        yesterday = today - timedelta(days=1)
        
        invalid_data = {
            'book_id': 1,
            'student_id': 1,
            'loan_date': today,
            'actual_return_date': yesterday  # Before loan date
        }
        
        errors = loans_manager.validate_loan_data(invalid_data)
        
        assert any('Actual return date cannot be before loan date' in error for error in errors)
    
    def test_validate_loan_data_invalid_status(self, loans_manager):
        """Test validation with invalid loan status"""
        invalid_data = {
            'book_id': 1,
            'student_id': 1,
            'loan_status': 'invalid_status'
        }
        
        errors = loans_manager.validate_loan_data(invalid_data)
        
        assert any("Loan status must be" in error for error in errors)
    
    def test_validate_loan_data_returned_without_return_date(self, loans_manager):
        """Test validation with returned status but no return date"""
        invalid_data = {
            'book_id': 1,
            'student_id': 1,
            'loan_status': 'returned'
            # Missing actual_return_date
        }
        
        errors = loans_manager.validate_loan_data(invalid_data)
        
        assert any('Returned loans must have an actual return date' in error for error in errors)
    
    def test_validate_loan_data_active_with_return_date(self, loans_manager):
        """Test validation with active status but has return date"""
        invalid_data = {
            'book_id': 1,
            'student_id': 1,
            'loan_status': 'active',
            'actual_return_date': date.today()
        }
        
        errors = loans_manager.validate_loan_data(invalid_data)
        
        assert any('Active loans cannot have an actual return date' in error for error in errors)
    
    def test_validate_loan_data_negative_renewal_count(self, loans_manager):
        """Test validation with negative renewal count"""
        invalid_data = {
            'book_id': 1,
            'student_id': 1,
            'renewal_count': -1
        }
        
        errors = loans_manager.validate_loan_data(invalid_data)
        
        assert any('Renewal count cannot be negative' in error for error in errors)
    
    def test_create_loan_success(self, loans_manager, mock_connection):
        """Test successful loan creation"""
        mock_connection.execute_query.return_value = [{'loan_id': 1}]
        
        result = loans_manager.create_loan(1, 1)
        
        assert result == 1
        mock_connection.execute_query.assert_called_once()
    
    def test_create_loan_with_estimated_return_date(self, loans_manager, mock_connection):
        """Test loan creation with estimated return date"""
        mock_connection.execute_query.return_value = [{'loan_id': 1}]
        return_date = date.today() + timedelta(days=14)
        
        result = loans_manager.create_loan(1, 1, estimated_return_date=return_date)
        
        assert result == 1
        mock_connection.execute_query.assert_called_once()
    
    def test_create_loan_validation_failure(self, loans_manager, mock_connection):
        """Test loan creation with validation failure"""
        # This will fail validation due to missing required fields
        result = loans_manager.create_loan(None, None)
        
        assert result is None
        mock_connection.execute_query.assert_not_called()
    
    def test_create_loan_database_error(self, loans_manager, mock_connection):
        """Test loan creation with database error"""
        mock_connection.execute_query.side_effect = Exception("Database error")
        
        result = loans_manager.create_loan(1, 1)
        
        assert result is None
    
    def test_return_book_success(self, loans_manager, mock_connection):
        """Test successful book return"""
        mock_connection.execute_command.return_value = 1
        
        result = loans_manager.return_book(1)
        
        assert result is True
        mock_connection.execute_command.assert_called_once()
    
    def test_return_book_failure(self, loans_manager, mock_connection):
        """Test failed book return"""
        mock_connection.execute_command.return_value = 0
        
        result = loans_manager.return_book(1)
        
        assert result is False
    
    def test_return_book_with_date(self, loans_manager, mock_connection):
        """Test book return with specific date"""
        mock_connection.execute_command.return_value = 1
        return_date = date.today()
        
        result = loans_manager.return_book(1, return_date)
        
        assert result is True
        args, kwargs = mock_connection.execute_command.call_args
        assert return_date in args[1]
    
    def test_renew_loan_success(self, loans_manager, mock_connection):
        """Test successful loan renewal"""
        mock_connection.execute_command.return_value = 1
        new_date = date.today() + timedelta(days=14)
        
        result = loans_manager.renew_loan(1, new_date)
        
        assert result is True
        mock_connection.execute_command.assert_called_once()
    
    def test_renew_loan_failure(self, loans_manager, mock_connection):
        """Test failed loan renewal"""
        mock_connection.execute_command.return_value = 0
        new_date = date.today() + timedelta(days=14)
        
        result = loans_manager.renew_loan(1, new_date)
        
        assert result is False
    
    def test_get_active_loans_all(self, loans_manager, mock_connection):
        """Test getting all active loans"""
        mock_data = [
            {
                'loan_id': 1,
                'book_title': 'Test Book',
                'student_name': 'John Doe',
                'loan_status': 'active'
            }
        ]
        mock_connection.execute_query.return_value = mock_data
        
        result = loans_manager.get_active_loans()
        
        assert result == mock_data
        mock_connection.execute_query.assert_called_once()
    
    def test_get_active_loans_for_student(self, loans_manager, mock_connection):
        """Test getting active loans for specific student"""
        mock_data = [
            {
                'loan_id': 1,
                'book_title': 'Test Book',
                'student_id': 1,
                'loan_status': 'active'
            }
        ]
        mock_connection.execute_query.return_value = mock_data
        
        result = loans_manager.get_active_loans(1)
        
        assert result == mock_data
        args, kwargs = mock_connection.execute_query.call_args
        assert 1 in args[1]
    
    def test_get_overdue_loans(self, loans_manager, mock_connection):
        """Test getting overdue loans"""
        mock_data = [
            {
                'loan_id': 1,
                'book_title': 'Overdue Book',
                'loan_status': 'overdue',
                'days_overdue': 5
            }
        ]
        mock_connection.execute_query.return_value = mock_data
        
        result = loans_manager.get_overdue_loans()
        
        assert result == mock_data
        mock_connection.execute_query.assert_called_once()
    
    def test_get_loan_history_all(self, loans_manager, mock_connection):
        """Test getting all loan history"""
        mock_data = [
            {
                'loan_id': 1,
                'book_title': 'Test Book',
                'loan_status': 'returned',
                'loan_duration': 10
            }
        ]
        mock_connection.execute_query.return_value = mock_data
        
        result = loans_manager.get_loan_history()
        
        assert result == mock_data
        mock_connection.execute_query.assert_called_once()
    
    def test_get_loan_history_for_student(self, loans_manager, mock_connection):
        """Test getting loan history for specific student"""
        mock_data = [
            {
                'loan_id': 1,
                'student_id': 1,
                'book_title': 'Test Book',
                'loan_status': 'returned'
            }
        ]
        mock_connection.execute_query.return_value = mock_data
        
        result = loans_manager.get_loan_history(student_id=1)
        
        assert result == mock_data
        args, kwargs = mock_connection.execute_query.call_args
        assert 1 in args[1]
    
    def test_get_loan_history_for_book(self, loans_manager, mock_connection):
        """Test getting loan history for specific book"""
        mock_data = [
            {
                'loan_id': 1,
                'book_id': 1,
                'book_title': 'Test Book',
                'loan_status': 'returned'
            }
        ]
        mock_connection.execute_query.return_value = mock_data
        
        result = loans_manager.get_loan_history(book_id=1)
        
        assert result == mock_data
        args, kwargs = mock_connection.execute_query.call_args
        assert 1 in args[1]
    
    def test_update_overdue_loans(self, loans_manager, mock_connection):
        """Test updating overdue loans"""
        mock_connection.execute_query.return_value = [{'updated_count': 5}]
        
        result = loans_manager.update_overdue_loans()
        
        assert result == 5
        mock_connection.execute_query.assert_called_once()
    
    def test_get_loan_statistics(self, loans_manager, mock_connection):
        """Test getting loan statistics"""
        mock_data = [
            {
                'total_loans': 100,
                'active_loans': 25,
                'overdue_loans': 5,
                'returned_loans': 70,
                'avg_loan_duration': 12.5
            }
        ]
        mock_connection.execute_query.return_value = mock_data
        
        result = loans_manager.get_loan_statistics()
        
        assert result == mock_data[0]
        mock_connection.execute_query.assert_called_once()
    
    def test_get_student_loan_summary(self, loans_manager, mock_connection):
        """Test getting student loan summary"""
        mock_data = [
            {
                'total_loans': 10,
                'current_loans': 2,
                'overdue_loans': 1,
                'late_returns': 3
            }
        ]
        mock_connection.execute_query.return_value = mock_data
        
        result = loans_manager.get_student_loan_summary(1)
        
        assert result == mock_data[0]
        args, kwargs = mock_connection.execute_query.call_args
        assert 1 in args[1]


class TestLoansTableConstraints:
    """Test database constraints for Loans table"""
    
    def test_date_constraints(self):
        """Test date constraints"""
        manager = LoansTableManager(Mock())
        
        today = date.today()
        yesterday = today - timedelta(days=1)
        tomorrow = today + timedelta(days=1)
        
        # Valid dates
        valid_data = {
            'book_id': 1,
            'student_id': 1,
            'loan_date': today,
            'estimated_return_date': tomorrow
        }
        
        errors = manager.validate_loan_data(valid_data)
        date_errors = [e for e in errors if 'date' in e.lower()]
        assert len(date_errors) == 0
        
        # Invalid dates
        invalid_data = {
            'book_id': 1,
            'student_id': 1,
            'loan_date': today,
            'estimated_return_date': yesterday  # Before loan date
        }
        
        errors = manager.validate_loan_data(invalid_data)
        assert any('Estimated return date must be after loan date' in error for error in errors)
    
    def test_status_constraints(self):
        """Test status constraints"""
        manager = LoansTableManager(Mock())
        
        # Valid statuses
        valid_statuses = ['active', 'returned', 'overdue', 'lost']
        
        for status in valid_statuses:
            data = {
                'book_id': 1,
                'student_id': 1,
                'loan_status': status
            }
            
            # Add return date for returned status
            if status == 'returned':
                data['actual_return_date'] = date.today()
            
            errors = manager.validate_loan_data(data)
            status_errors = [e for e in errors if 'status' in e.lower() and 'must be' in e]
            assert len(status_errors) == 0, f"Valid status {status} should not have errors"
    
    def test_renewal_count_constraints(self):
        """Test renewal count constraints"""
        manager = LoansTableManager(Mock())
        
        # Valid renewal counts
        valid_counts = [0, 1, 5, 10]
        
        for count in valid_counts:
            data = {
                'book_id': 1,
                'student_id': 1,
                'renewal_count': count
            }
            
            errors = manager.validate_loan_data(data)
            count_errors = [e for e in errors if 'renewal count' in e.lower()]
            assert len(count_errors) == 0, f"Valid renewal count {count} should not have errors"
        
        # Invalid renewal count
        invalid_data = {
            'book_id': 1,
            'student_id': 1,
            'renewal_count': -1
        }
        
        errors = manager.validate_loan_data(invalid_data)
        assert any('Renewal count cannot be negative' in error for error in errors)


if __name__ == '__main__':
    pytest.main([__file__])