"""
Loan repository for CRUD operations and transaction management
"""

from datetime import date, timedelta
from typing import Dict, List, Optional, Any
from database.connection.database_connection import DatabaseConnection


class LoanRepository:
    """Repository for loan CRUD operations and transaction management"""
    
    def __init__(self, connection: DatabaseConnection):
        self.connection = connection
    
    def create_loan(self, book_id: int, student_id: int, loan_date: date = None, 
                   estimated_return_date: date = None, notes: str = None) -> Optional[int]:
        """Create a new loan"""
        try:
            if loan_date is None:
                loan_date = date.today()
            
            if estimated_return_date is None:
                estimated_return_date = loan_date + timedelta(days=14)
            
            query = """
            INSERT INTO loans (book_id, student_id, loan_date, estimated_return_date, notes)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING loan_id
            """
            
            params = (book_id, student_id, loan_date, estimated_return_date, notes)
            result = self.connection.execute_query(query, params)
            return result[0]['loan_id'] if result else None
            
        except Exception as e:
            print(f"Error creating loan: {e}")
            return None
    
    def get_by_id(self, loan_id: int) -> Optional[Dict[str, Any]]:
        """Get loan by ID with book and student info"""
        try:
            query = """
            SELECT l.*, 
                   b.title, b.author, b.isbn,
                   s.student_number, s.first_name, s.last_name, s.email
            FROM loans l
            JOIN books b ON l.book_id = b.book_id
            JOIN students s ON l.student_id = s.student_id
            WHERE l.loan_id = %s
            """
            result = self.connection.execute_query(query, (loan_id,))
            return result[0] if result else None
        except Exception as e:
            print(f"Error getting loan by ID: {e}")
            return None
    
    def get_active_loans(self, student_id: int = None) -> List[Dict[str, Any]]:
        """Get active loans, optionally for specific student"""
        try:
            if student_id:
                query = """
                SELECT l.*, b.title, b.author, b.isbn,
                       s.student_number, s.first_name, s.last_name
                FROM loans l
                JOIN books b ON l.book_id = b.book_id
                JOIN students s ON l.student_id = s.student_id
                WHERE l.loan_status IN ('active', 'overdue') AND l.student_id = %s
                ORDER BY l.estimated_return_date
                """
                params = (student_id,)
            else:
                query = """
                SELECT l.*, b.title, b.author, b.isbn,
                       s.student_number, s.first_name, s.last_name
                FROM loans l
                JOIN books b ON l.book_id = b.book_id
                JOIN students s ON l.student_id = s.student_id
                WHERE l.loan_status IN ('active', 'overdue')
                ORDER BY l.estimated_return_date
                """
                params = None
            
            return self.connection.execute_query(query, params)
        except Exception as e:
            print(f"Error getting active loans: {e}")
            return []
    
    def get_overdue_loans(self) -> List[Dict[str, Any]]:
        """Get overdue loans"""
        try:
            query = """
            SELECT l.*, b.title, b.author, b.isbn,
                   s.student_number, s.first_name, s.last_name, s.email,
                   CURRENT_DATE - l.estimated_return_date as days_overdue
            FROM loans l
            JOIN books b ON l.book_id = b.book_id
            JOIN students s ON l.student_id = s.student_id
            WHERE l.loan_status = 'overdue' 
               OR (l.loan_status = 'active' AND l.estimated_return_date < CURRENT_DATE)
            ORDER BY l.estimated_return_date
            """
            return self.connection.execute_query(query)
        except Exception as e:
            print(f"Error getting overdue loans: {e}")
            return []
    
    def return_book(self, loan_id: int, return_date: date = None) -> bool:
        """Return a book"""
        try:
            if return_date is None:
                return_date = date.today()
            
            query = """
            UPDATE loans 
            SET loan_status = 'returned', actual_return_date = %s
            WHERE loan_id = %s AND loan_status IN ('active', 'overdue')
            """
            
            rows_affected = self.connection.execute_command(query, (return_date, loan_id))
            return rows_affected > 0
            
        except Exception as e:
            print(f"Error returning book: {e}")
            return False
    
    def renew_loan(self, loan_id: int, new_return_date: date) -> bool:
        """Renew a loan"""
        try:
            query = """
            UPDATE loans 
            SET estimated_return_date = %s, renewal_count = renewal_count + 1
            WHERE loan_id = %s AND loan_status = 'active'
            """
            
            rows_affected = self.connection.execute_command(query, (new_return_date, loan_id))
            return rows_affected > 0
            
        except Exception as e:
            print(f"Error renewing loan: {e}")
            return False
    
    def update_status(self, loan_id: int, status: str) -> bool:
        """Update loan status"""
        try:
            query = "UPDATE loans SET loan_status = %s WHERE loan_id = %s"
            rows_affected = self.connection.execute_command(query, (status, loan_id))
            return rows_affected > 0
        except Exception as e:
            print(f"Error updating loan status: {e}")
            return False
    
    def get_loan_history(self, student_id: int = None, book_id: int = None) -> List[Dict[str, Any]]:
        """Get loan history"""
        try:
            base_query = """
            SELECT l.*, b.title, b.author, b.isbn,
                   s.student_number, s.first_name, s.last_name,
                   CASE 
                       WHEN l.actual_return_date IS NOT NULL 
                       THEN l.actual_return_date - l.loan_date
                       ELSE CURRENT_DATE - l.loan_date
                   END as loan_duration
            FROM loans l
            JOIN books b ON l.book_id = b.book_id
            JOIN students s ON l.student_id = s.student_id
            """
            
            where_clauses = []
            params = []
            
            if student_id:
                where_clauses.append("l.student_id = %s")
                params.append(student_id)
            
            if book_id:
                where_clauses.append("l.book_id = %s")
                params.append(book_id)
            
            if where_clauses:
                base_query += " WHERE " + " AND ".join(where_clauses)
            
            base_query += " ORDER BY l.loan_date DESC"
            
            return self.connection.execute_query(base_query, tuple(params) if params else None)
        except Exception as e:
            print(f"Error getting loan history: {e}")
            return []
    
    def update_overdue_loans(self) -> int:
        """Update loans that are past due to overdue status"""
        try:
            query = """
            UPDATE loans 
            SET loan_status = 'overdue'
            WHERE loan_status = 'active' 
              AND actual_return_date IS NULL 
              AND estimated_return_date < CURRENT_DATE
            """
            
            rows_affected = self.connection.execute_command(query)
            return rows_affected
        except Exception as e:
            print(f"Error updating overdue loans: {e}")
            return 0
    
    def get_loan_stats(self) -> Dict[str, Any]:
        """Get loan statistics"""
        try:
            query = """
            SELECT 
                COUNT(*) as total_loans,
                COUNT(CASE WHEN loan_status = 'active' THEN 1 END) as active_loans,
                COUNT(CASE WHEN loan_status = 'overdue' THEN 1 END) as overdue_loans,
                COUNT(CASE WHEN loan_status = 'returned' THEN 1 END) as returned_loans,
                COUNT(CASE WHEN loan_status = 'lost' THEN 1 END) as lost_loans,
                AVG(CASE WHEN actual_return_date IS NOT NULL 
                    THEN actual_return_date - loan_date END) as avg_loan_duration,
                COUNT(CASE WHEN actual_return_date > estimated_return_date THEN 1 END) as late_returns
            FROM loans
            """
            result = self.connection.execute_query(query)
            return result[0] if result else {}
        except Exception as e:
            print(f"Error getting loan stats: {e}")
            return {}
    
    def get_student_loan_summary(self, student_id: int) -> Dict[str, Any]:
        """Get loan summary for specific student"""
        try:
            query = """
            SELECT 
                COUNT(*) as total_loans,
                COUNT(CASE WHEN loan_status IN ('active', 'overdue') THEN 1 END) as current_loans,
                COUNT(CASE WHEN loan_status = 'overdue' THEN 1 END) as overdue_loans,
                COUNT(CASE WHEN actual_return_date > estimated_return_date THEN 1 END) as late_returns,
                MAX(loan_date) as last_loan_date
            FROM loans
            WHERE student_id = %s
            """
            result = self.connection.execute_query(query, (student_id,))
            return result[0] if result else {}
        except Exception as e:
            print(f"Error getting student loan summary: {e}")
            return {}