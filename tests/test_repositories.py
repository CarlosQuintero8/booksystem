"""
Unit tests for repository classes
"""

import pytest
from unittest.mock import Mock
from database.repositories.student_repository import StudentRepository
from database.repositories.book_repository import BookRepository
from database.repositories.loan_repository import LoanRepository
from database.repositories.shelf_repository import ShelfRepository


class TestStudentRepository:
    """Test StudentRepository"""
    
    @pytest.fixture
    def mock_connection(self):
        return Mock()
    
    @pytest.fixture
    def student_repo(self, mock_connection):
        return StudentRepository(mock_connection)
    
    def test_create_student(self, student_repo, mock_connection):
        mock_connection.execute_query.return_value = [{'student_id': 1}]
        
        student_data = {
            'student_number': '2024001',
            'first_name': 'Juan',
            'last_name': 'Pérez',
            'email': 'juan@test.com'
        }
        
        result = student_repo.create(student_data)
        assert result == 1
        mock_connection.execute_query.assert_called_once()
    
    def test_get_by_id(self, student_repo, mock_connection):
        mock_data = {'student_id': 1, 'first_name': 'Juan'}
        mock_connection.execute_query.return_value = [mock_data]
        
        result = student_repo.get_by_id(1)
        assert result == mock_data


class TestBookRepository:
    """Test BookRepository"""
    
    @pytest.fixture
    def mock_connection(self):
        return Mock()
    
    @pytest.fixture
    def book_repo(self, mock_connection):
        return BookRepository(mock_connection)
    
    def test_create_book(self, book_repo, mock_connection):
        mock_connection.execute_query.return_value = [{'book_id': 1}]
        
        book_data = {
            'title': 'Test Book',
            'author': 'Test Author',
            'shelf_id': 1
        }
        
        result = book_repo.create(book_data)
        assert result == 1
    
    def test_search_books(self, book_repo, mock_connection):
        mock_data = [{'book_id': 1, 'title': 'Test Book'}]
        mock_connection.execute_query.return_value = mock_data
        
        result = book_repo.search('Test')
        assert result == mock_data


class TestLoanRepository:
    """Test LoanRepository"""
    
    @pytest.fixture
    def mock_connection(self):
        return Mock()
    
    @pytest.fixture
    def loan_repo(self, mock_connection):
        return LoanRepository(mock_connection)
    
    def test_create_loan(self, loan_repo, mock_connection):
        mock_connection.execute_query.return_value = [{'loan_id': 1}]
        
        result = loan_repo.create_loan(1, 1)
        assert result == 1
    
    def test_return_book(self, loan_repo, mock_connection):
        mock_connection.execute_command.return_value = 1
        
        result = loan_repo.return_book(1)
        assert result is True


class TestShelfRepository:
    """Test ShelfRepository"""
    
    @pytest.fixture
    def mock_connection(self):
        return Mock()
    
    @pytest.fixture
    def shelf_repo(self, mock_connection):
        return ShelfRepository(mock_connection)
    
    def test_create_shelf(self, shelf_repo, mock_connection):
        mock_connection.execute_query.return_value = [{'shelf_id': 1}]
        
        shelf_data = {
            'location_code': 'A1',
            'section': 'Section A',
            'main_topic': 'Science',
            'total_capacity': 50
        }
        
        result = shelf_repo.create(shelf_data)
        assert result == 1
    
    def test_check_capacity(self, shelf_repo, mock_connection):
        mock_connection.execute_query.return_value = [{'has_capacity': True}]
        
        result = shelf_repo.check_capacity(1)
        assert result is True