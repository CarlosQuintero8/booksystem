"""
Unit tests for Books table creation and validation
"""

import pytest
import os
import sys
from unittest.mock import Mock, patch

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from database.config.database_config import DatabaseConfig, DatabaseType
from database.connection.database_connection import DatabaseConnection
from database.tables.books_table import BooksTableManager


class TestBooksTable:
    """Test cases for Books table management"""
    
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
    def books_manager(self, mock_connection):
        """Create BooksTableManager instance"""
        return BooksTableManager(mock_connection)
    
    def test_init_with_postgresql(self, mock_connection):
        """Test initialization with PostgreSQL connection"""
        manager = BooksTableManager(mock_connection)
        assert manager.connection == mock_connection
    
    def test_create_table_success(self, books_manager, mock_connection):
        """Test successful table creation"""
        mock_connection.execute_script.return_value = None
        mock_connection.execute_command.return_value = None
        
        result = books_manager.create_table()
        
        assert result is True
        assert mock_connection.execute_script.called
        assert mock_connection.execute_command.called
    
    def test_create_table_failure(self, books_manager, mock_connection):
        """Test table creation failure"""
        mock_connection.execute_script.side_effect = Exception("Database error")
        
        result = books_manager.create_table()
        
        assert result is False
    
    def test_drop_table_success(self, books_manager, mock_connection):
        """Test successful table drop"""
        mock_connection.execute_command.return_value = None
        
        result = books_manager.drop_table()
        
        assert result is True
        # Should drop views, functions, and table
        assert mock_connection.execute_command.call_count >= 5
    
    def test_drop_table_failure(self, books_manager, mock_connection):
        """Test table drop failure"""
        mock_connection.execute_command.side_effect = Exception("Database error")
        
        result = books_manager.drop_table()
        
        assert result is False
    
    def test_table_exists(self, books_manager, mock_connection):
        """Test table existence check"""
        mock_connection.table_exists.return_value = True
        
        result = books_manager.table_exists()
        
        assert result is True
        mock_connection.table_exists.assert_called_with('books')
    
    def test_validate_book_data_valid(self, books_manager):
        """Test validation with valid book data"""
        valid_data = {
            'title': 'Introduction to Computer Science',
            'author': 'John Doe',
            'publisher': 'Tech Publications',
            'publication_year': 2023,
            'isbn': '9781234567890',
            'pages': 350,
            'book_type': 'physical',
            'shelf_id': 1,
            'status': 'available',
            'language': 'English'
        }
        
        errors = books_manager.validate_book_data(valid_data)
        
        assert len(errors) == 0
    
    def test_validate_book_data_missing_required_fields(self, books_manager):
        """Test validation with missing required fields"""
        invalid_data = {
            'publisher': 'Tech Publications',
            'pages': 350
            # Missing title and author
        }
        
        errors = books_manager.validate_book_data(invalid_data)
        
        assert len(errors) >= 2
        assert any('title is required' in error for error in errors)
        assert any('author is required' in error for error in errors)
    
    def test_validate_book_data_empty_title(self, books_manager):
        """Test validation with empty title"""
        invalid_data = {
            'title': '   ',  # Empty after trim
            'author': 'John Doe'
        }
        
        errors = books_manager.validate_book_data(invalid_data)
        
        assert any('title is required and cannot be empty' in error for error in errors)
    
    def test_validate_book_data_empty_author(self, books_manager):
        """Test validation with empty author"""
        invalid_data = {
            'title': 'Some Title',
            'author': ''  # Empty
        }
        
        errors = books_manager.validate_book_data(invalid_data)
        
        assert any('author is required and cannot be empty' in error for error in errors)
    
    def test_validate_book_data_invalid_isbn(self, books_manager):
        """Test validation with invalid ISBN"""
        invalid_data = {
            'title': 'Some Title',
            'author': 'John Doe',
            'isbn': '123'  # Too short
        }
        
        errors = books_manager.validate_book_data(invalid_data)
        
        assert any('ISBN must be in valid format' in error for error in errors)
    
    def test_validate_book_data_invalid_publication_year(self, books_manager):
        """Test validation with invalid publication year"""
        invalid_data = {
            'title': 'Some Title',
            'author': 'John Doe',
            'publication_year': 500  # Too old
        }
        
        errors = books_manager.validate_book_data(invalid_data)
        
        assert any('Publication year must be between' in error for error in errors)
    
    def test_validate_book_data_invalid_pages(self, books_manager):
        """Test validation with invalid pages"""
        invalid_data = {
            'title': 'Some Title',
            'author': 'John Doe',
            'pages': -10  # Negative
        }
        
        errors = books_manager.validate_book_data(invalid_data)
        
        assert any('Pages must be a positive integer' in error for error in errors)
    
    def test_validate_book_data_invalid_book_type(self, books_manager):
        """Test validation with invalid book type"""
        invalid_data = {
            'title': 'Some Title',
            'author': 'John Doe',
            'book_type': 'invalid_type'
        }
        
        errors = books_manager.validate_book_data(invalid_data)
        
        assert any("Book type must be 'physical' or 'digital'" in error for error in errors)
    
    def test_validate_book_data_invalid_status(self, books_manager):
        """Test validation with invalid status"""
        invalid_data = {
            'title': 'Some Title',
            'author': 'John Doe',
            'status': 'invalid_status'
        }
        
        errors = books_manager.validate_book_data(invalid_data)
        
        assert any("Status must be" in error for error in errors)
    
    def test_validate_book_data_physical_book_without_shelf(self, books_manager):
        """Test validation with physical book without shelf"""
        invalid_data = {
            'title': 'Some Title',
            'author': 'John Doe',
            'book_type': 'physical'
            # Missing shelf_id
        }
        
        errors = books_manager.validate_book_data(invalid_data)
        
        assert any('Physical books must be assigned to a shelf' in error for error in errors)
    
    def test_validate_book_data_digital_book_with_shelf(self, books_manager):
        """Test validation with digital book assigned to shelf"""
        invalid_data = {
            'title': 'Some Title',
            'author': 'John Doe',
            'book_type': 'digital',
            'shelf_id': 1  # Digital books shouldn't have shelf
        }
        
        errors = books_manager.validate_book_data(invalid_data)
        
        assert any('Digital books cannot be assigned to a shelf' in error for error in errors)
    
    def test_validate_isbn_valid_isbn10(self, books_manager):
        """Test ISBN validation with valid ISBN-10"""
        assert books_manager._validate_isbn('0123456789') is True
        assert books_manager._validate_isbn('012345678X') is True
        assert books_manager._validate_isbn('0-123-45678-9') is True
    
    def test_validate_isbn_valid_isbn13(self, books_manager):
        """Test ISBN validation with valid ISBN-13"""
        assert books_manager._validate_isbn('9781234567890') is True
        assert books_manager._validate_isbn('9791234567890') is True
        assert books_manager._validate_isbn('978-1-234-56789-0') is True
    
    def test_validate_isbn_invalid(self, books_manager):
        """Test ISBN validation with invalid ISBNs"""
        assert books_manager._validate_isbn('123') is False
        assert books_manager._validate_isbn('12345678901234') is False
        assert books_manager._validate_isbn('abcd567890') is False
        assert books_manager._validate_isbn('9761234567890') is False  # Wrong prefix
    
    def test_get_book_inventory_no_filters(self, books_manager, mock_connection):
        """Test getting book inventory without filters"""
        mock_data = [
            {
                'book_id': 1,
                'title': 'Test Book',
                'author': 'Test Author',
                'status': 'available'
            }
        ]
        mock_connection.execute_query.return_value = mock_data
        
        result = books_manager.get_book_inventory()
        
        assert result == mock_data
        mock_connection.execute_query.assert_called_once()
    
    def test_get_book_inventory_with_filters(self, books_manager, mock_connection):
        """Test getting book inventory with filters"""
        mock_data = [
            {
                'book_id': 1,
                'title': 'Test Book',
                'author': 'Test Author',
                'status': 'available'
            }
        ]
        mock_connection.execute_query.return_value = mock_data
        
        filters = {'status': 'available', 'author': 'Test'}
        result = books_manager.get_book_inventory(filters)
        
        assert result == mock_data
        mock_connection.execute_query.assert_called_once()
    
    def test_get_available_books(self, books_manager, mock_connection):
        """Test getting available books"""
        mock_data = [
            {
                'book_id': 1,
                'title': 'Available Book',
                'status': 'available'
            }
        ]
        mock_connection.execute_query.return_value = mock_data
        
        result = books_manager.get_available_books()
        
        assert result == mock_data
        mock_connection.execute_query.assert_called_once()
    
    def test_get_books_by_shelf_all(self, books_manager, mock_connection):
        """Test getting all books by shelf"""
        mock_data = [
            {
                'shelf_id': 1,
                'location_code': 'A1',
                'books': [{'book_id': 1, 'title': 'Test Book'}]
            }
        ]
        mock_connection.execute_query.return_value = mock_data
        
        result = books_manager.get_books_by_shelf()
        
        assert result == mock_data
        mock_connection.execute_query.assert_called_once()
    
    def test_get_books_by_shelf_specific(self, books_manager, mock_connection):
        """Test getting books for specific shelf"""
        mock_data = [
            {
                'shelf_id': 1,
                'location_code': 'A1',
                'books': [{'book_id': 1, 'title': 'Test Book'}]
            }
        ]
        mock_connection.execute_query.return_value = mock_data
        
        result = books_manager.get_books_by_shelf(1)
        
        assert result == mock_data
        args, kwargs = mock_connection.execute_query.call_args
        assert 1 in args or '1' in str(args)
    
    def test_search_books(self, books_manager, mock_connection):
        """Test searching books"""
        mock_data = [
            {
                'book_id': 1,
                'title': 'Computer Science',
                'author': 'John Doe'
            }
        ]
        mock_connection.execute_query.return_value = mock_data
        
        result = books_manager.search_books('Computer')
        
        assert result == mock_data
        mock_connection.execute_query.assert_called_once()
    
    def test_get_book_statistics(self, books_manager, mock_connection):
        """Test getting book statistics"""
        mock_data = [
            {
                'total_books': 100,
                'physical_books': 80,
                'digital_books': 20,
                'available_books': 75
            }
        ]
        mock_connection.execute_query.return_value = mock_data
        
        result = books_manager.get_book_statistics()
        
        assert result == mock_data[0]
        mock_connection.execute_query.assert_called_once()
    
    def test_move_book_to_shelf_success(self, books_manager, mock_connection):
        """Test successful book move to shelf"""
        mock_connection.execute_command.return_value = 1
        
        result = books_manager.move_book_to_shelf(1, 2)
        
        assert result is True
        mock_connection.execute_command.assert_called_once()
    
    def test_move_book_to_shelf_failure(self, books_manager, mock_connection):
        """Test failed book move to shelf"""
        mock_connection.execute_command.return_value = 0
        
        result = books_manager.move_book_to_shelf(1, 2)
        
        assert result is False
    
    def test_update_book_status_success(self, books_manager, mock_connection):
        """Test successful book status update"""
        mock_connection.execute_command.return_value = 1
        
        result = books_manager.update_book_status(1, 'loaned')
        
        assert result is True
        mock_connection.execute_command.assert_called_once()
    
    def test_update_book_status_invalid_status(self, books_manager, mock_connection):
        """Test book status update with invalid status"""
        result = books_manager.update_book_status(1, 'invalid_status')
        
        assert result is False
        mock_connection.execute_command.assert_not_called()
    
    def test_update_book_status_failure(self, books_manager, mock_connection):
        """Test failed book status update"""
        mock_connection.execute_command.return_value = 0
        
        result = books_manager.update_book_status(1, 'loaned')
        
        assert result is False


class TestBooksTableConstraints:
    """Test database constraints for Books table"""
    
    def test_isbn_format_constraints(self):
        """Test ISBN format constraints"""
        manager = BooksTableManager(Mock())
        
        # Valid ISBNs
        valid_isbns = [
            '0123456789',      # ISBN-10
            '012345678X',      # ISBN-10 with X
            '9781234567890',   # ISBN-13
            '9791234567890'    # ISBN-13 with 979 prefix
        ]
        
        for isbn in valid_isbns:
            assert manager._validate_isbn(isbn), f"Valid ISBN {isbn} should pass validation"
        
        # Invalid ISBNs
        invalid_isbns = [
            '123',             # Too short
            '12345678901234',  # Too long
            'abcd567890',      # Contains letters
            '9761234567890'    # Wrong prefix
        ]
        
        for isbn in invalid_isbns:
            assert not manager._validate_isbn(isbn), f"Invalid ISBN {isbn} should fail validation"
    
    def test_book_type_constraints(self):
        """Test book type constraints"""
        manager = BooksTableManager(Mock())
        
        # Valid book types
        valid_data_physical = {
            'title': 'Test Book',
            'author': 'Test Author',
            'book_type': 'physical',
            'shelf_id': 1
        }
        
        valid_data_digital = {
            'title': 'Test Book',
            'author': 'Test Author',
            'book_type': 'digital'
        }
        
        errors_physical = manager.validate_book_data(valid_data_physical)
        errors_digital = manager.validate_book_data(valid_data_digital)
        
        type_errors_physical = [e for e in errors_physical if 'book type' in e.lower()]
        type_errors_digital = [e for e in errors_digital if 'book type' in e.lower()]
        
        assert len(type_errors_physical) == 0
        assert len(type_errors_digital) == 0
    
    def test_shelf_relationship_constraints(self):
        """Test shelf relationship constraints"""
        manager = BooksTableManager(Mock())
        
        # Physical book without shelf should fail
        invalid_physical = {
            'title': 'Test Book',
            'author': 'Test Author',
            'book_type': 'physical'
            # Missing shelf_id
        }
        
        errors = manager.validate_book_data(invalid_physical)
        assert any('Physical books must be assigned to a shelf' in error for error in errors)
        
        # Digital book with shelf should fail
        invalid_digital = {
            'title': 'Test Book',
            'author': 'Test Author',
            'book_type': 'digital',
            'shelf_id': 1
        }
        
        errors = manager.validate_book_data(invalid_digital)
        assert any('Digital books cannot be assigned to a shelf' in error for error in errors)


if __name__ == '__main__':
    pytest.main([__file__])