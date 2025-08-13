"""
Shelf repository for CRUD operations and capacity tracking
"""

from typing import Dict, List, Optional, Any
from database.connection.database_connection import DatabaseConnection


class ShelfRepository:
    """Repository for shelf CRUD operations and capacity tracking"""
    
    def __init__(self, connection: DatabaseConnection):
        self.connection = connection
    
    def create(self, shelf_data: Dict[str, Any]) -> Optional[int]:
        """Create a new shelf"""
        try:
            query = """
            INSERT INTO shelves (location_code, section, main_topic, material, total_capacity)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING shelf_id
            """
            
            params = (
                shelf_data.get('location_code'),
                shelf_data.get('section'),
                shelf_data.get('main_topic'),
                shelf_data.get('material'),
                shelf_data.get('total_capacity')
            )
            
            result = self.connection.execute_query(query, params)
            return result[0]['shelf_id'] if result else None
            
        except Exception as e:
            print(f"Error creating shelf: {e}")
            return None
    
    def get_by_id(self, shelf_id: int) -> Optional[Dict[str, Any]]:
        """Get shelf by ID"""
        try:
            query = "SELECT * FROM shelves WHERE shelf_id = %s"
            result = self.connection.execute_query(query, (shelf_id,))
            return result[0] if result else None
        except Exception as e:
            print(f"Error getting shelf by ID: {e}")
            return None
    
    def get_by_location_code(self, location_code: str) -> Optional[Dict[str, Any]]:
        """Get shelf by location code"""
        try:
            query = "SELECT * FROM shelves WHERE location_code = %s"
            result = self.connection.execute_query(query, (location_code,))
            return result[0] if result else None
        except Exception as e:
            print(f"Error getting shelf by location code: {e}")
            return None
    
    def get_all(self) -> List[Dict[str, Any]]:
        """Get all shelves"""
        try:
            query = "SELECT * FROM shelves ORDER BY location_code"
            return self.connection.execute_query(query)
        except Exception as e:
            print(f"Error getting all shelves: {e}")
            return []
    
    def get_by_section(self, section: str) -> List[Dict[str, Any]]:
        """Get shelves by section"""
        try:
            query = "SELECT * FROM shelves WHERE section = %s ORDER BY location_code"
            return self.connection.execute_query(query, (section,))
        except Exception as e:
            print(f"Error getting shelves by section: {e}")
            return []
    
    def get_by_topic(self, topic: str) -> List[Dict[str, Any]]:
        """Get shelves by topic"""
        try:
            query = "SELECT * FROM shelves WHERE main_topic ILIKE %s ORDER BY location_code"
            return self.connection.execute_query(query, (f"%{topic}%",))
        except Exception as e:
            print(f"Error getting shelves by topic: {e}")
            return []
    
    def get_available_shelves(self, min_capacity: int = 1) -> List[Dict[str, Any]]:
        """Get shelves with available capacity"""
        try:
            query = """
            SELECT * FROM shelves 
            WHERE (total_capacity - current_book_count) >= %s 
            ORDER BY (total_capacity - current_book_count) DESC, location_code
            """
            return self.connection.execute_query(query, (min_capacity,))
        except Exception as e:
            print(f"Error getting available shelves: {e}")
            return []
    
    def get_utilization_report(self) -> List[Dict[str, Any]]:
        """Get shelf utilization report"""
        try:
            query = """
            SELECT 
                shelf_id,
                location_code,
                section,
                main_topic,
                total_capacity,
                current_book_count,
                (total_capacity - current_book_count) as available_space,
                ROUND((current_book_count::DECIMAL / total_capacity::DECIMAL) * 100, 2) as utilization_percentage,
                CASE 
                    WHEN current_book_count = 0 THEN 'Empty'
                    WHEN current_book_count = total_capacity THEN 'Full'
                    WHEN (current_book_count::DECIMAL / total_capacity::DECIMAL) > 0.8 THEN 'Nearly Full'
                    WHEN (current_book_count::DECIMAL / total_capacity::DECIMAL) > 0.5 THEN 'Half Full'
                    ELSE 'Available'
                END as status
            FROM shelves
            ORDER BY location_code
            """
            return self.connection.execute_query(query)
        except Exception as e:
            print(f"Error getting utilization report: {e}")
            return []
    
    def update(self, shelf_id: int, shelf_data: Dict[str, Any]) -> bool:
        """Update shelf"""
        try:
            fields = []
            params = []
            
            for field in ['location_code', 'section', 'main_topic', 'material', 'total_capacity']:
                if field in shelf_data:
                    fields.append(f"{field} = %s")
                    params.append(shelf_data[field])
            
            if not fields:
                return False
            
            params.append(shelf_id)
            query = f"UPDATE shelves SET {', '.join(fields)} WHERE shelf_id = %s"
            
            rows_affected = self.connection.execute_command(query, tuple(params))
            return rows_affected > 0
            
        except Exception as e:
            print(f"Error updating shelf: {e}")
            return False
    
    def delete(self, shelf_id: int) -> bool:
        """Delete shelf (only if empty)"""
        try:
            # First check if shelf is empty
            query = "SELECT current_book_count FROM shelves WHERE shelf_id = %s"
            result = self.connection.execute_query(query, (shelf_id,))
            
            if not result:
                return False
            
            if result[0]['current_book_count'] > 0:
                print(f"Cannot delete shelf {shelf_id}: contains books")
                return False
            
            query = "DELETE FROM shelves WHERE shelf_id = %s"
            rows_affected = self.connection.execute_command(query, (shelf_id,))
            return rows_affected > 0
            
        except Exception as e:
            print(f"Error deleting shelf: {e}")
            return False
    
    def get_books_on_shelf(self, shelf_id: int) -> List[Dict[str, Any]]:
        """Get all books on a shelf"""
        try:
            query = """
            SELECT * FROM books 
            WHERE shelf_id = %s AND book_type = 'physical'
            ORDER BY title, author
            """
            return self.connection.execute_query(query, (shelf_id,))
        except Exception as e:
            print(f"Error getting books on shelf: {e}")
            return []
    
    def check_capacity(self, shelf_id: int) -> bool:
        """Check if shelf has available capacity"""
        try:
            query = "SELECT (total_capacity - current_book_count) > 0 as has_capacity FROM shelves WHERE shelf_id = %s"
            result = self.connection.execute_query(query, (shelf_id,))
            return result[0]['has_capacity'] if result else False
        except Exception as e:
            print(f"Error checking shelf capacity: {e}")
            return False
    
    def get_capacity_stats(self) -> Dict[str, Any]:
        """Get overall capacity statistics"""
        try:
            query = """
            SELECT 
                COUNT(*) as total_shelves,
                SUM(total_capacity) as total_capacity,
                SUM(current_book_count) as total_books,
                SUM(total_capacity - current_book_count) as total_available_space,
                ROUND(AVG(current_book_count::DECIMAL / total_capacity::DECIMAL * 100), 2) as avg_utilization,
                COUNT(CASE WHEN current_book_count = total_capacity THEN 1 END) as full_shelves,
                COUNT(CASE WHEN current_book_count = 0 THEN 1 END) as empty_shelves
            FROM shelves
            """
            result = self.connection.execute_query(query)
            return result[0] if result else {}
        except Exception as e:
            print(f"Error getting capacity stats: {e}")
            return {}
    
    def validate_capacity_consistency(self) -> List[Dict[str, Any]]:
        """Validate shelf capacity consistency"""
        try:
            query = """
            SELECT 
                s.shelf_id,
                s.location_code,
                COUNT(b.book_id) as actual_book_count,
                s.current_book_count as recorded_count,
                CASE 
                    WHEN COUNT(b.book_id) = s.current_book_count THEN 'OK'
                    ELSE 'MISMATCH'
                END as status
            FROM shelves s
            LEFT JOIN books b ON s.shelf_id = b.shelf_id AND b.book_type = 'physical'
            GROUP BY s.shelf_id, s.location_code, s.current_book_count
            HAVING COUNT(b.book_id) != s.current_book_count
            ORDER BY s.location_code
            """
            return self.connection.execute_query(query)
        except Exception as e:
            print(f"Error validating capacity consistency: {e}")
            return []
    
    def fix_capacity_counts(self) -> int:
        """Fix shelf capacity count mismatches"""
        try:
            query = """
            UPDATE shelves 
            SET current_book_count = (
                SELECT COUNT(*) 
                FROM books 
                WHERE books.shelf_id = shelves.shelf_id 
                  AND books.book_type = 'physical'
            )
            """
            rows_affected = self.connection.execute_command(query)
            return rows_affected
        except Exception as e:
            print(f"Error fixing capacity counts: {e}")
            return 0