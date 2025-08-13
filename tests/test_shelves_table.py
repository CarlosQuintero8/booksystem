"""
Unit tests for Shelves table creation and validation
"""

import pytest
import os
import sys
from unittest.mock import Mock, patch

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from database.config.database_config import DatabaseConfig, DatabaseType
from database.connection.database_connection import DatabaseConnection
from database.tables.shelves_table import ShelvesTableManager


class TestShelvesTable:
    """Test cases for Shelves table management"""
    
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
    def shelves_manager(self, mock_connection):
        """Create ShelvesTableManager instance"""
        return ShelvesTableManager(mock_connection)
    
    def test_init_with_postgresql(self, mock_connection):
        """Test initialization with PostgreSQL connection"""
        manager = ShelvesTableManager(mock_connection)
        assert manager.connection == mock_connection
    
    def test_create_table_success(self, shelves_manager, mock_connection):
        """Test successful table creation"""
        mock_connection.execute_script.return_value = None
        mock_connection.execute_command.return_value = None
        
        result = shelves_manager.create_table()
        
        assert result is True
        assert mock_connection.execute_script.called
        assert mock_connection.execute_command.called
    
    def test_create_table_failure(self, shelves_manager, mock_connection):
        """Test table creation failure"""
        mock_connection.execute_script.side_effect = Exception("Database error")
        
        result = shelves_manager.create_table()
        
        assert result is False
    
    def test_drop_table_success(self, shelves_manager, mock_connection):
        """Test successful table drop"""
        mock_connection.execute_command.return_value = None
        
        result = shelves_manager.drop_table()
        
        assert result is True
        # Should drop view, functions, and table
        assert mock_connection.execute_command.call_count >= 3
    
    def test_drop_table_failure(self, shelves_manager, mock_connection):
        """Test table drop failure"""
        mock_connection.execute_command.side_effect = Exception("Database error")
        
        result = shelves_manager.drop_table()
        
        assert result is False
    
    def test_table_exists(self, shelves_manager, mock_connection):
        """Test table existence check"""
        mock_connection.table_exists.return_value = True
        
        result = shelves_manager.table_exists()
        
        assert result is True
        mock_connection.table_exists.assert_called_with('shelves')
    
    def test_validate_shelf_data_valid(self, shelves_manager):
        """Test validation with valid shelf data"""
        valid_data = {
            'location_code': 'A1',
            'section': 'Section A',
            'main_topic': 'Computer Science',
            'material': 'Wood',
            'total_capacity': 50,
            'current_book_count': 25
        }
        
        errors = shelves_manager.validate_shelf_data(valid_data)
        
        assert len(errors) == 0
    
    def test_validate_shelf_data_missing_required_fields(self, shelves_manager):
        """Test validation with missing required fields"""
        invalid_data = {
            'section': 'Section A',
            'material': 'Wood'
            # Missing location_code, main_topic, total_capacity
        }
        
        errors = shelves_manager.validate_shelf_data(invalid_data)
        
        assert len(errors) >= 3
        assert any('location_code is required' in error for error in errors)
        assert any('main_topic is required' in error for error in errors)
        assert any('total_capacity is required' in error for error in errors)
    
    def test_validate_shelf_data_invalid_location_code(self, shelves_manager):
        """Test validation with invalid location code"""
        invalid_data = {
            'location_code': 'ABC123',  # Invalid format
            'section': 'Section A',
            'main_topic': 'Science',
            'total_capacity': 50
        }
        
        errors = shelves_manager.validate_shelf_data(invalid_data)
        
        assert any('Location code must be in format' in error for error in errors)
    
    def test_validate_shelf_data_empty_section(self, shelves_manager):
        """Test validation with empty section"""
        invalid_data = {
            'location_code': 'A1',
            'section': '   ',  # Empty after trim
            'main_topic': 'Science',
            'total_capacity': 50
        }
        
        errors = shelves_manager.validate_shelf_data(invalid_data)
        
        assert any('Section cannot be empty' in error for error in errors)
    
    def test_validate_shelf_data_empty_main_topic(self, shelves_manager):
        """Test validation with empty main topic"""
        invalid_data = {
            'location_code': 'A1',
            'section': 'Section A',
            'main_topic': '',  # Empty
            'total_capacity': 50
        }
        
        errors = shelves_manager.validate_shelf_data(invalid_data)
        
        assert any('Main topic cannot be empty' in error for error in errors)
    
    def test_validate_shelf_data_invalid_total_capacity(self, shelves_manager):
        """Test validation with invalid total capacity"""
        invalid_data = {
            'location_code': 'A1',
            'section': 'Section A',
            'main_topic': 'Science',
            'total_capacity': -5  # Negative capacity
        }
        
        errors = shelves_manager.validate_shelf_data(invalid_data)
        
        assert any('Total capacity must be a positive integer' in error for error in errors)
    
    def test_validate_shelf_data_invalid_current_book_count(self, shelves_manager):
        """Test validation with invalid current book count"""
        invalid_data = {
            'location_code': 'A1',
            'section': 'Section A',
            'main_topic': 'Science',
            'total_capacity': 50,
            'current_book_count': -1  # Negative count
        }
        
        errors = shelves_manager.validate_shelf_data(invalid_data)
        
        assert any('Current book count cannot be negative' in error for error in errors)
    
    def test_validate_shelf_data_book_count_exceeds_capacity(self, shelves_manager):
        """Test validation with book count exceeding capacity"""
        invalid_data = {
            'location_code': 'A1',
            'section': 'Section A',
            'main_topic': 'Science',
            'total_capacity': 50,
            'current_book_count': 60  # Exceeds capacity
        }
        
        errors = shelves_manager.validate_shelf_data(invalid_data)
        
        assert any('Current book count cannot exceed total capacity' in error for error in errors)
    
    def test_validate_shelf_data_invalid_material(self, shelves_manager):
        """Test validation with invalid material"""
        invalid_data = {
            'location_code': 'A1',
            'section': 'Section A',
            'main_topic': 'Science',
            'total_capacity': 50,
            'material': 'InvalidMaterial'
        }
        
        errors = shelves_manager.validate_shelf_data(invalid_data)
        
        assert any('Material must be one of' in error for error in errors)
    
    def test_check_capacity_success(self, shelves_manager, mock_connection):
        """Test successful capacity check"""
        mock_connection.execute_query.return_value = [{'has_capacity': True}]
        
        result = shelves_manager.check_capacity(1)
        
        assert result is True
        mock_connection.execute_query.assert_called_once()
    
    def test_check_capacity_failure(self, shelves_manager, mock_connection):
        """Test capacity check failure"""
        mock_connection.execute_query.side_effect = Exception("Database error")
        
        result = shelves_manager.check_capacity(1)
        
        assert result is False
    
    def test_update_book_count_success(self, shelves_manager, mock_connection):
        """Test successful book count update"""
        mock_connection.execute_command.return_value = None
        
        result = shelves_manager.update_book_count(1, 5)
        
        assert result is True
        mock_connection.execute_command.assert_called_once()
    
    def test_update_book_count_failure(self, shelves_manager, mock_connection):
        """Test book count update failure"""
        mock_connection.execute_command.side_effect = Exception("Database error")
        
        result = shelves_manager.update_book_count(1, 5)
        
        assert result is False
    
    def test_get_shelf_utilization_all(self, shelves_manager, mock_connection):
        """Test getting all shelf utilization"""
        mock_data = [
            {
                'shelf_id': 1,
                'location_code': 'A1',
                'utilization_percentage': 75.0,
                'status': 'Half Full'
            }
        ]
        mock_connection.execute_query.return_value = mock_data
        
        result = shelves_manager.get_shelf_utilization()
        
        assert result == mock_data
        mock_connection.execute_query.assert_called_once()
    
    def test_get_shelf_utilization_specific(self, shelves_manager, mock_connection):
        """Test getting specific shelf utilization"""
        mock_data = [
            {
                'shelf_id': 1,
                'location_code': 'A1',
                'utilization_percentage': 75.0,
                'status': 'Half Full'
            }
        ]
        mock_connection.execute_query.return_value = mock_data
        
        result = shelves_manager.get_shelf_utilization(1)
        
        assert result == mock_data
        args, kwargs = mock_connection.execute_query.call_args
        assert '1' in str(args) or 1 in args
    
    def test_get_available_shelves(self, shelves_manager, mock_connection):
        """Test getting available shelves"""
        mock_data = [
            {
                'shelf_id': 1,
                'location_code': 'A1',
                'available_space': 25,
                'status': 'Available'
            }
        ]
        mock_connection.execute_query.return_value = mock_data
        
        result = shelves_manager.get_available_shelves(10)
        
        assert result == mock_data
        mock_connection.execute_query.assert_called_once()
    
    def test_get_shelves_by_topic(self, shelves_manager, mock_connection):
        """Test getting shelves by topic"""
        mock_data = [
            {
                'shelf_id': 1,
                'location_code': 'A1',
                'main_topic': 'Computer Science'
            }
        ]
        mock_connection.execute_query.return_value = mock_data
        
        result = shelves_manager.get_shelves_by_topic('Computer')
        
        assert result == mock_data
        mock_connection.execute_query.assert_called_once()
    
    def test_get_capacity_report(self, shelves_manager, mock_connection):
        """Test getting capacity report"""
        mock_data = [
            {
                'total_shelves': 10,
                'total_capacity': 500,
                'total_books': 300,
                'avg_utilization': 60.0
            }
        ]
        mock_connection.execute_query.return_value = mock_data
        
        result = shelves_manager.get_capacity_report()
        
        assert result == mock_data[0]
        mock_connection.execute_query.assert_called_once()


class TestShelvesTableConstraints:
    """Test database constraints for Shelves table"""
    
    def test_location_code_format_constraint(self):
        """Test location code format constraint"""
        manager = ShelvesTableManager(Mock())
        
        # Valid location codes
        valid_codes = ['A1', 'B2', 'C10', 'Z99']
        for code in valid_codes:
            data = {
                'location_code': code,
                'section': 'Section A',
                'main_topic': 'Science',
                'total_capacity': 50
            }
            errors = manager.validate_shelf_data(data)
            code_errors = [e for e in errors if 'Location code' in e]
            assert len(code_errors) == 0, f"Valid code {code} should not have errors"
        
        # Invalid location codes
        invalid_codes = ['1A', 'AB', '123', 'A', 'A123']
        for code in invalid_codes:
            data = {
                'location_code': code,
                'section': 'Section A',
                'main_topic': 'Science',
                'total_capacity': 50
            }
            errors = manager.validate_shelf_data(data)
            code_errors = [e for e in errors if 'Location code' in e]
            assert len(code_errors) > 0, f"Invalid code {code} should have errors"
    
    def test_material_constraint(self):
        """Test material constraint"""
        manager = ShelvesTableManager(Mock())
        
        # Valid materials
        valid_materials = ['Wood', 'Metal', 'Plastic', 'Glass', 'Composite', None]
        for material in valid_materials:
            data = {
                'location_code': 'A1',
                'section': 'Section A',
                'main_topic': 'Science',
                'total_capacity': 50,
                'material': material
            }
            errors = manager.validate_shelf_data(data)
            material_errors = [e for e in errors if 'Material' in e]
            assert len(material_errors) == 0, f"Valid material {material} should not have errors"
    
    def test_capacity_constraints(self):
        """Test capacity constraints"""
        manager = ShelvesTableManager(Mock())
        
        # Test positive capacity requirement
        data = {
            'location_code': 'A1',
            'section': 'Section A',
            'main_topic': 'Science',
            'total_capacity': 0
        }
        errors = manager.validate_shelf_data(data)
        assert any('positive integer' in error for error in errors)
        
        # Test current count vs capacity
        data = {
            'location_code': 'A1',
            'section': 'Section A',
            'main_topic': 'Science',
            'total_capacity': 10,
            'current_book_count': 15
        }
        errors = manager.validate_shelf_data(data)
        assert any('exceed total capacity' in error for error in errors)


if __name__ == '__main__':
    pytest.main([__file__])