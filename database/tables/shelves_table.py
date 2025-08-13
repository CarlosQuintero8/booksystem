"""
Shelves table creation and management for PostgreSQL
"""

from typing import Dict, List, Optional, Any
from database.connection.database_connection import DatabaseConnection
from database.config.database_config import DatabaseType


class ShelvesTableManager:
    """Manages Shelves table creation and operations for PostgreSQL"""
    
    def __init__(self, connection: DatabaseConnection):
        self.connection = connection
        if connection.config.db_type != DatabaseType.POSTGRESQL:
            raise ValueError("ShelvesTableManager only supports PostgreSQL")
    
    def create_table(self) -> bool:
        """Create Shelves table with PostgreSQL-specific constraints"""
        
        try:
            return self._create_postgresql_table()
        except Exception as e:
            print(f"Error creating Shelves table: {e}")
            return False
    
    def _create_postgresql_table(self) -> bool:
        """Create Shelves table for PostgreSQL"""
        
        sql = """
        CREATE TABLE IF NOT EXISTS shelves (
            shelf_id SERIAL PRIMARY KEY,
            location_code VARCHAR(10) UNIQUE NOT NULL,
            section VARCHAR(50) NOT NULL,
            main_topic VARCHAR(100) NOT NULL,
            material VARCHAR(50),
            total_capacity INTEGER NOT NULL,
            current_book_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            -- Constraints
            CONSTRAINT chk_location_code_format CHECK (location_code ~ '^[A-Z][0-9]{1,2}$'),
            CONSTRAINT chk_section_not_empty CHECK (LENGTH(TRIM(section)) > 0),
            CONSTRAINT chk_main_topic_not_empty CHECK (LENGTH(TRIM(main_topic)) > 0),
            CONSTRAINT chk_total_capacity_positive CHECK (total_capacity > 0),
            CONSTRAINT chk_current_book_count_valid CHECK (current_book_count >= 0 AND current_book_count <= total_capacity),
            CONSTRAINT chk_material_valid CHECK (material IS NULL OR material IN ('Wood', 'Metal', 'Plastic', 'Glass', 'Composite'))
        );
        """
        
        self.connection.execute_script(sql)
        self._create_indexes()
        self._create_triggers()
        self._create_functions()
        self._create_views()
        return True
    
    def _create_indexes(self):
        """Create indexes for PostgreSQL"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_shelves_location_code ON shelves(location_code);",
            "CREATE INDEX IF NOT EXISTS idx_shelves_section ON shelves(section);",
            "CREATE INDEX IF NOT EXISTS idx_shelves_main_topic ON shelves(main_topic);",
            "CREATE INDEX IF NOT EXISTS idx_shelves_material ON shelves(material);",
            "CREATE INDEX IF NOT EXISTS idx_shelves_capacity ON shelves(total_capacity, current_book_count);"
        ]
        
        for index_sql in indexes:
            self.connection.execute_command(index_sql)
    
    def _create_triggers(self):
        """Create triggers for PostgreSQL"""
        # Update timestamp trigger
        trigger_function = """
        CREATE OR REPLACE FUNCTION update_shelves_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
        
        trigger = """
        CREATE TRIGGER trigger_shelves_updated_at
            BEFORE UPDATE ON shelves
            FOR EACH ROW
            EXECUTE FUNCTION update_shelves_updated_at();
        """
        
        self.connection.execute_script(trigger_function)
        self.connection.execute_command(trigger)
    
    def _create_functions(self):
        """Create utility functions for shelf management"""
        
        # Function to check shelf capacity
        capacity_function = """
        CREATE OR REPLACE FUNCTION check_shelf_capacity(shelf_id_param INTEGER)
        RETURNS BOOLEAN AS $$
        DECLARE
            current_count INTEGER;
            max_capacity INTEGER;
        BEGIN
            SELECT current_book_count, total_capacity
            INTO current_count, max_capacity
            FROM shelves
            WHERE shelf_id = shelf_id_param;
            
            IF NOT FOUND THEN
                RAISE EXCEPTION 'Shelf with ID % not found', shelf_id_param;
            END IF;
            
            RETURN current_count < max_capacity;
        END;
        $$ LANGUAGE plpgsql;
        """
        
        # Function to update shelf book count
        update_count_function = """
        CREATE OR REPLACE FUNCTION update_shelf_book_count(shelf_id_param INTEGER, count_change INTEGER)
        RETURNS VOID AS $$
        DECLARE
            new_count INTEGER;
            max_capacity INTEGER;
        BEGIN
            SELECT current_book_count + count_change, total_capacity
            INTO new_count, max_capacity
            FROM shelves
            WHERE shelf_id = shelf_id_param;
            
            IF NOT FOUND THEN
                RAISE EXCEPTION 'Shelf with ID % not found', shelf_id_param;
            END IF;
            
            IF new_count < 0 THEN
                RAISE EXCEPTION 'Cannot have negative book count on shelf %', shelf_id_param;
            END IF;
            
            IF new_count > max_capacity THEN
                RAISE EXCEPTION 'Shelf % capacity exceeded. Current: %, Max: %', shelf_id_param, new_count, max_capacity;
            END IF;
            
            UPDATE shelves
            SET current_book_count = new_count
            WHERE shelf_id = shelf_id_param;
        END;
        $$ LANGUAGE plpgsql;
        """
        
        self.connection.execute_script(capacity_function)
        self.connection.execute_script(update_count_function)
    
    def _create_views(self):
        """Create utility views for shelf analysis"""
        
        utilization_view = """
        CREATE OR REPLACE VIEW shelf_utilization AS
        SELECT 
            shelf_id,
            location_code,
            section,
            main_topic,
            material,
            total_capacity,
            current_book_count,
            ROUND((current_book_count::DECIMAL / total_capacity::DECIMAL) * 100, 2) as utilization_percentage,
            (total_capacity - current_book_count) as available_space,
            CASE 
                WHEN current_book_count = 0 THEN 'Empty'
                WHEN current_book_count = total_capacity THEN 'Full'
                WHEN (current_book_count::DECIMAL / total_capacity::DECIMAL) > 0.8 THEN 'Nearly Full'
                WHEN (current_book_count::DECIMAL / total_capacity::DECIMAL) > 0.5 THEN 'Half Full'
                ELSE 'Available'
            END as status,
            created_at,
            updated_at
        FROM shelves;
        """
        
        self.connection.execute_script(utilization_view)
    
    def drop_table(self) -> bool:
        """Drop Shelves table and related objects"""
        try:
            # Drop in reverse order of dependencies
            self.connection.execute_command("DROP VIEW IF EXISTS shelf_utilization;")
            self.connection.execute_command("DROP FUNCTION IF EXISTS update_shelf_book_count(INTEGER, INTEGER);")
            self.connection.execute_command("DROP FUNCTION IF EXISTS check_shelf_capacity(INTEGER);")
            self.connection.execute_command("DROP TABLE IF EXISTS shelves;")
            return True
        except Exception as e:
            print(f"Error dropping Shelves table: {e}")
            return False
    
    def table_exists(self) -> bool:
        """Check if Shelves table exists"""
        return self.connection.table_exists('shelves')
    
    def validate_shelf_data(self, shelf_data: dict) -> list:
        """Validate shelf data before insertion"""
        errors = []
        
        # Required fields
        required_fields = ['location_code', 'section', 'main_topic', 'total_capacity']
        for field in required_fields:
            if not shelf_data.get(field):
                errors.append(f"{field} is required")
        
        # Location code format validation
        location_code = shelf_data.get('location_code', '')
        if location_code:
            import re
            if not re.match(r'^[A-Z][0-9]{1,2}$', location_code):
                errors.append("Location code must be in format: Letter followed by 1-2 digits (e.g., A1, B12)")
        
        # Section validation
        section = shelf_data.get('section', '')
        if section and len(section.strip()) == 0:
            errors.append("Section cannot be empty")
        
        # Main topic validation
        main_topic = shelf_data.get('main_topic', '')
        if main_topic and len(main_topic.strip()) == 0:
            errors.append("Main topic cannot be empty")
        
        # Total capacity validation
        total_capacity = shelf_data.get('total_capacity')
        if total_capacity is not None:
            try:
                capacity = int(total_capacity)
                if capacity <= 0:
                    errors.append("Total capacity must be a positive integer")
            except (ValueError, TypeError):
                errors.append("Total capacity must be a valid integer")
        
        # Current book count validation
        current_book_count = shelf_data.get('current_book_count', 0)
        if current_book_count is not None:
            try:
                count = int(current_book_count)
                if count < 0:
                    errors.append("Current book count cannot be negative")
                elif total_capacity and count > int(total_capacity):
                    errors.append("Current book count cannot exceed total capacity")
            except (ValueError, TypeError):
                errors.append("Current book count must be a valid integer")
        
        # Material validation
        material = shelf_data.get('material')
        if material:
            valid_materials = ['Wood', 'Metal', 'Plastic', 'Glass', 'Composite']
            if material not in valid_materials:
                errors.append(f"Material must be one of: {', '.join(valid_materials)}")
        
        return errors
    
    def check_capacity(self, shelf_id: int) -> bool:
        """Check if shelf has available capacity"""
        try:
            result = self.connection.execute_query(
                "SELECT check_shelf_capacity(%s) as has_capacity",
                (shelf_id,)
            )
            return result[0]['has_capacity'] if result else False
        except Exception as e:
            print(f"Error checking shelf capacity: {e}")
            return False
    
    def update_book_count(self, shelf_id: int, count_change: int) -> bool:
        """Update shelf book count"""
        try:
            self.connection.execute_command(
                "SELECT update_shelf_book_count(%s, %s)",
                (shelf_id, count_change)
            )
            return True
        except Exception as e:
            print(f"Error updating shelf book count: {e}")
            return False
    
    def get_shelf_utilization(self, shelf_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get shelf utilization information"""
        try:
            if shelf_id:
                query = "SELECT * FROM shelf_utilization WHERE shelf_id = %s"
                params = (shelf_id,)
            else:
                query = "SELECT * FROM shelf_utilization ORDER BY location_code"
                params = None
            
            return self.connection.execute_query(query, params)
        except Exception as e:
            print(f"Error getting shelf utilization: {e}")
            return []
    
    def get_available_shelves(self, min_capacity: int = 1) -> List[Dict[str, Any]]:
        """Get shelves with available capacity"""
        try:
            query = """
            SELECT * FROM shelf_utilization 
            WHERE available_space >= %s 
            ORDER BY available_space DESC, location_code
            """
            return self.connection.execute_query(query, (min_capacity,))
        except Exception as e:
            print(f"Error getting available shelves: {e}")
            return []
    
    def get_shelves_by_topic(self, topic: str) -> List[Dict[str, Any]]:
        """Get shelves by main topic"""
        try:
            query = """
            SELECT * FROM shelf_utilization 
            WHERE main_topic ILIKE %s 
            ORDER BY location_code
            """
            return self.connection.execute_query(query, (f"%{topic}%",))
        except Exception as e:
            print(f"Error getting shelves by topic: {e}")
            return []
    
    def get_capacity_report(self) -> Dict[str, Any]:
        """Get overall capacity report"""
        try:
            query = """
            SELECT 
                COUNT(*) as total_shelves,
                SUM(total_capacity) as total_capacity,
                SUM(current_book_count) as total_books,
                SUM(available_space) as total_available_space,
                ROUND(AVG(utilization_percentage), 2) as avg_utilization,
                COUNT(CASE WHEN status = 'Full' THEN 1 END) as full_shelves,
                COUNT(CASE WHEN status = 'Nearly Full' THEN 1 END) as nearly_full_shelves,
                COUNT(CASE WHEN status = 'Empty' THEN 1 END) as empty_shelves
            FROM shelf_utilization
            """
            result = self.connection.execute_query(query)
            return result[0] if result else {}
        except Exception as e:
            print(f"Error getting capacity report: {e}")
            return {}