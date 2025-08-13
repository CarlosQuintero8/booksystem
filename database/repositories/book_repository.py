"""
Book repository for CRUD operations and inventory management
"""

from typing import Dict, List, Optional, Any
from database.connection.database_connection import DatabaseConnection


class BookRepository:
    """Repository for book CRUD operations and inventory management"""
    
    def __init__(self, connection: DatabaseConnection):
        self.connection = connection
    
    def create(self, book_data: Dict[str, Any]) -> Optional[int]:
        """Create a new book"""
        try:
            query = """
            INSERT INTO books (isbn, title, author, publisher, publication_year, edition, 
                             language, pages, book_type, shelf_id, status, acquisition_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING book_id
            """
            
            params = (
                book_data.get('isbn'),
                book_data.get('title'),
                book_data.get('author'),
                book_data.get('publisher'),
                book_data.get('publication_year'),
                book_data.get('edition'),
                book_data.get('language', 'Spanish'),
                book_data.get('pages'),
                book_data.get('book_type', 'physical'),
                book_data.get('shelf_id'),
                book_data.get('status', 'available'),
                book_data.get('acquisition_date')
            )
            
            result = self.connection.execute_query(query, params)
            return result[0]['book_id'] if result else None
            
        except Exception as e:
            print(f"Error creating book: {e}")
            return None
    
    def get_by_id(self, book_id: int) -> Optional[Dict[str, Any]]:
        """Get book by ID with shelf info"""
        try:
            query = """
            SELECT b.*, s.location_code, s.section, s.main_topic
            FROM books b
            LEFT JOIN shelves s ON b.shelf_id = s.shelf_id
            WHERE b.book_id = %s
            """
            result = self.connection.execute_query(query, (book_id,))
            return result[0] if result else None
        except Exception as e:
            print(f"Error getting book by ID: {e}")
            return None
    
    def get_by_isbn(self, isbn: str) -> Optional[Dict[str, Any]]:
        """Get book by ISBN"""
        try:
            query = "SELECT * FROM books WHERE isbn = %s"
            result = self.connection.execute_query(query, (isbn,))
            return result[0] if result else None
        except Exception as e:
            print(f"Error getting book by ISBN: {e}")
            return None
    
    def search(self, search_term: str, fields: List[str] = None) -> List[Dict[str, Any]]:
        """Search books by multiple fields"""
        try:
            if not fields:
                fields = ['title', 'author', 'publisher', 'isbn']
            
            where_clauses = [f"{field} ILIKE %s" for field in fields]
            params = [f"%{search_term}%" for _ in fields]
            
            query = f"""
            SELECT b.*, s.location_code, s.section
            FROM books b
            LEFT JOIN shelves s ON b.shelf_id = s.shelf_id
            WHERE {' OR '.join(where_clauses)}
            ORDER BY b.title, b.author
            """
            
            return self.connection.execute_query(query, tuple(params))
        except Exception as e:
            print(f"Error searching books: {e}")
            return []
    
    def get_available(self) -> List[Dict[str, Any]]:
        """Get all available books"""
        try:
            query = """
            SELECT b.*, s.location_code, s.section
            FROM books b
            LEFT JOIN shelves s ON b.shelf_id = s.shelf_id
            WHERE b.status = 'available'
            ORDER BY b.title, b.author
            """
            return self.connection.execute_query(query)
        except Exception as e:
            print(f"Error getting available books: {e}")
            return []
    
    def get_by_shelf(self, shelf_id: int) -> List[Dict[str, Any]]:
        """Get books on specific shelf"""
        try:
            query = """
            SELECT * FROM books 
            WHERE shelf_id = %s 
            ORDER BY title, author
            """
            return self.connection.execute_query(query, (shelf_id,))
        except Exception as e:
            print(f"Error getting books by shelf: {e}")
            return []
    
    def get_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Get books by status"""
        try:
            query = """
            SELECT b.*, s.location_code, s.section
            FROM books b
            LEFT JOIN shelves s ON b.shelf_id = s.shelf_id
            WHERE b.status = %s
            ORDER BY b.title, b.author
            """
            return self.connection.execute_query(query, (status,))
        except Exception as e:
            print(f"Error getting books by status: {e}")
            return []
    
    def update(self, book_id: int, book_data: Dict[str, Any]) -> bool:
        """Update book"""
        try:
            fields = []
            params = []
            
            for field in ['isbn', 'title', 'author', 'publisher', 'publication_year', 
                         'edition', 'language', 'pages', 'book_type', 'shelf_id', 
                         'status', 'acquisition_date']:
                if field in book_data:
                    fields.append(f"{field} = %s")
                    params.append(book_data[field])
            
            if not fields:
                return False
            
            params.append(book_id)
            query = f"UPDATE books SET {', '.join(fields)} WHERE book_id = %s"
            
            rows_affected = self.connection.execute_command(query, tuple(params))
            return rows_affected > 0
            
        except Exception as e:
            print(f"Error updating book: {e}")
            return False
    
    def delete(self, book_id: int) -> bool:
        """Delete book"""
        try:
            query = "DELETE FROM books WHERE book_id = %s"
            rows_affected = self.connection.execute_command(query, (book_id,))
            return rows_affected > 0
        except Exception as e:
            print(f"Error deleting book: {e}")
            return False
    
    def move_to_shelf(self, book_id: int, shelf_id: int) -> bool:
        """Move book to different shelf"""
        try:
            query = "UPDATE books SET shelf_id = %s WHERE book_id = %s AND book_type = 'physical'"
            rows_affected = self.connection.execute_command(query, (shelf_id, book_id))
            return rows_affected > 0
        except Exception as e:
            print(f"Error moving book to shelf: {e}")
            return False
    
    def update_status(self, book_id: int, status: str) -> bool:
        """Update book status"""
        try:
            query = "UPDATE books SET status = %s WHERE book_id = %s"
            rows_affected = self.connection.execute_command(query, (status, book_id))
            return rows_affected > 0
        except Exception as e:
            print(f"Error updating book status: {e}")
            return False
    
    def get_inventory_stats(self) -> Dict[str, Any]:
        """Get inventory statistics"""
        try:
            query = """
            SELECT 
                COUNT(*) as total_books,
                COUNT(CASE WHEN book_type = 'physical' THEN 1 END) as physical_books,
                COUNT(CASE WHEN book_type = 'digital' THEN 1 END) as digital_books,
                COUNT(CASE WHEN status = 'available' THEN 1 END) as available_books,
                COUNT(CASE WHEN status = 'loaned' THEN 1 END) as loaned_books,
                COUNT(CASE WHEN status = 'maintenance' THEN 1 END) as maintenance_books,
                COUNT(CASE WHEN status = 'lost' THEN 1 END) as lost_books
            FROM books
            """
            result = self.connection.execute_query(query)
            return result[0] if result else {}
        except Exception as e:
            print(f"Error getting inventory stats: {e}")
            return {}
    
    def get_loan_history(self, book_id: int) -> List[Dict[str, Any]]:
        """Get loan history for book"""
        try:
            query = """
            SELECT l.*, s.student_number, s.first_name, s.last_name, s.email
            FROM loans l
            JOIN students s ON l.student_id = s.student_id
            WHERE l.book_id = %s
            ORDER BY l.loan_date DESC
            """
            return self.connection.execute_query(query, (book_id,))
        except Exception as e:
            print(f"Error getting loan history: {e}")
            return []