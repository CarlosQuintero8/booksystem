"""
Student repository for CRUD operations
"""

from typing import Dict, List, Optional, Any
from database.connection.database_connection import DatabaseConnection


class StudentRepository:
    """Repository for student CRUD operations"""
    
    def __init__(self, connection: DatabaseConnection):
        self.connection = connection
    
    def create(self, student_data: Dict[str, Any]) -> Optional[int]:
        """Create a new student"""
        try:
            query = """
            INSERT INTO students (student_number, first_name, last_name, email, phone, program, enrollment_year, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING student_id
            """
            
            params = (
                student_data.get('student_number'),
                student_data.get('first_name'),
                student_data.get('last_name'),
                student_data.get('email'),
                student_data.get('phone'),
                student_data.get('program'),
                student_data.get('enrollment_year'),
                student_data.get('status', 'active')
            )
            
            result = self.connection.execute_query(query, params)
            return result[0]['student_id'] if result else None
            
        except Exception as e:
            print(f"Error creating student: {e}")
            return None
    
    def get_by_id(self, student_id: int) -> Optional[Dict[str, Any]]:
        """Get student by ID"""
        try:
            query = "SELECT * FROM students WHERE student_id = %s"
            result = self.connection.execute_query(query, (student_id,))
            return result[0] if result else None
        except Exception as e:
            print(f"Error getting student by ID: {e}")
            return None
    
    def get_by_student_number(self, student_number: str) -> Optional[Dict[str, Any]]:
        """Get student by student number"""
        try:
            query = "SELECT * FROM students WHERE student_number = %s"
            result = self.connection.execute_query(query, (student_number,))
            return result[0] if result else None
        except Exception as e:
            print(f"Error getting student by number: {e}")
            return None
    
    def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get student by email"""
        try:
            query = "SELECT * FROM students WHERE email = %s"
            result = self.connection.execute_query(query, (email,))
            return result[0] if result else None
        except Exception as e:
            print(f"Error getting student by email: {e}")
            return None
    
    def search_by_name(self, name: str) -> List[Dict[str, Any]]:
        """Search students by name"""
        try:
            query = """
            SELECT * FROM students 
            WHERE first_name ILIKE %s OR last_name ILIKE %s 
            OR CONCAT(first_name, ' ', last_name) ILIKE %s
            ORDER BY last_name, first_name
            """
            search_term = f"%{name}%"
            return self.connection.execute_query(query, (search_term, search_term, search_term))
        except Exception as e:
            print(f"Error searching students by name: {e}")
            return []
    
    def get_all(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all students, optionally filtered by status"""
        try:
            if status:
                query = "SELECT * FROM students WHERE status = %s ORDER BY last_name, first_name"
                params = (status,)
            else:
                query = "SELECT * FROM students ORDER BY last_name, first_name"
                params = None
            
            return self.connection.execute_query(query, params)
        except Exception as e:
            print(f"Error getting all students: {e}")
            return []
    
    def update(self, student_id: int, student_data: Dict[str, Any]) -> bool:
        """Update student"""
        try:
            # Build dynamic update query
            fields = []
            params = []
            
            for field in ['student_number', 'first_name', 'last_name', 'email', 'phone', 'program', 'enrollment_year', 'status']:
                if field in student_data:
                    fields.append(f"{field} = %s")
                    params.append(student_data[field])
            
            if not fields:
                return False
            
            params.append(student_id)
            query = f"UPDATE students SET {', '.join(fields)} WHERE student_id = %s"
            
            rows_affected = self.connection.execute_command(query, tuple(params))
            return rows_affected > 0
            
        except Exception as e:
            print(f"Error updating student: {e}")
            return False
    
    def delete(self, student_id: int) -> bool:
        """Delete student"""
        try:
            query = "DELETE FROM students WHERE student_id = %s"
            rows_affected = self.connection.execute_command(query, (student_id,))
            return rows_affected > 0
        except Exception as e:
            print(f"Error deleting student: {e}")
            return False
    
    def get_loan_history(self, student_id: int) -> List[Dict[str, Any]]:
        """Get loan history for student"""
        try:
            query = """
            SELECT l.*, b.title, b.author, b.isbn
            FROM loans l
            JOIN books b ON l.book_id = b.book_id
            WHERE l.student_id = %s
            ORDER BY l.loan_date DESC
            """
            return self.connection.execute_query(query, (student_id,))
        except Exception as e:
            print(f"Error getting loan history: {e}")
            return []
    
    def get_active_loans(self, student_id: int) -> List[Dict[str, Any]]:
        """Get active loans for student"""
        try:
            query = """
            SELECT l.*, b.title, b.author, b.isbn
            FROM loans l
            JOIN books b ON l.book_id = b.book_id
            WHERE l.student_id = %s AND l.loan_status IN ('active', 'overdue')
            ORDER BY l.estimated_return_date
            """
            return self.connection.execute_query(query, (student_id,))
        except Exception as e:
            print(f"Error getting active loans: {e}")
            return []