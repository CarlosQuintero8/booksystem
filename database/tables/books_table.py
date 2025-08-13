"""
Books table creation and management for PostgreSQL
"""

import re
from typing import Dict, List, Optional, Any
from database.connection.database_connection import DatabaseConnection
from database.config.database_config import DatabaseType


class BooksTableManager:
    """Manages Books table creation and operations for PostgreSQL"""
    
    def __init__(self, connection: DatabaseConnection):
        self.connection = connection
        if connection.config.db_type != DatabaseType.POSTGRESQL:
            raise ValueError("BooksTableManager only supports PostgreSQL")
    
    def create_table(self) -> bool:
        """Create Books table with PostgreSQL-specific constraints"""
        
        try:
            return self._create_postgresql_table()
        except Exception as e:
            print(f"Error creating Books table: {e}")
            return False
    
    def _create_postgresql_table(self) -> bool:
        """Create Books table for PostgreSQL"""
        
        sql = """
        CREATE TABLE IF NOT EXISTS books (
            book_id SERIAL PRIMARY KEY,
            isbn VARCHAR(20) UNIQUE,
            title VARCHAR(500) NOT NULL,
            author VARCHAR(300) NOT NULL,
            publisher VARCHAR(200),
            publication_year INTEGER,
            edition VARCHAR(50),
            language VARCHAR(50) DEFAULT 'Spanish',
            pages INTEGER,
            book_type VARCHAR(20) DEFAULT 'physical' CHECK (book_type IN ('physical', 'digital')),
            shelf_id INTEGER REFERENCES shelves(shelf_id) ON DELETE SET NULL ON UPDATE CASCADE,
            status VARCHAR(20) DEFAULT 'available' CHECK (status IN ('available', 'loaned', 'maintenance', 'lost')),
            acquisition_date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            -- Constraints
            CONSTRAINT chk_isbn_format CHECK (isbn IS NULL OR isbn ~ '^(97[89])?[0-9]{9}[0-9X]$'),
            CONSTRAINT chk_title_not_empty CHECK (LENGTH(TRIM(title)) > 0),
            CONSTRAINT chk_author_not_empty CHECK (LENGTH(TRIM(author)) > 0),
            CONSTRAINT chk_publication_year_valid CHECK (publication_year IS NULL OR (publication_year >= 1000 AND publication_year <= EXTRACT(YEAR FROM CURRENT_DATE) + 1)),
            CONSTRAINT chk_pages_positive CHECK (pages IS NULL OR pages > 0),
            CONSTRAINT chk_acquisition_date_valid CHECK (acquisition_date IS NULL OR acquisition_date <= CURRENT_DATE),
            CONSTRAINT chk_physical_book_has_shelf CHECK (book_type = 'digital' OR shelf_id IS NOT NULL),
            CONSTRAINT chk_digital_book_no_shelf CHECK (book_type = 'physical' OR shelf_id IS NULL)
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
            "CREATE INDEX IF NOT EXISTS idx_books_isbn ON books(isbn);",
            "CREATE INDEX IF NOT EXISTS idx_books_title ON books(title);",
            "CREATE INDEX IF NOT EXISTS idx_books_author ON books(author);",
            "CREATE INDEX IF NOT EXISTS idx_books_publisher ON books(publisher);",
            "CREATE INDEX IF NOT EXISTS idx_books_status ON books(status);",
            "CREATE INDEX IF NOT EXISTS idx_books_book_type ON books(book_type);",
            "CREATE INDEX IF NOT EXISTS idx_books_shelf_id ON books(shelf_id);",
            "CREATE INDEX IF NOT EXISTS idx_books_publication_year ON books(publication_year);",
            "CREATE INDEX IF NOT EXISTS idx_books_language ON books(language);",
            "CREATE INDEX IF NOT EXISTS idx_books_title_author ON books(title, author);"
        ]
        
        for index_sql in indexes:
            self.connection.execute_command(index_sql)
    
    def _create_triggers(self):
        """Create triggers for PostgreSQL"""
        # Update timestamp trigger
        trigger_function = """
        CREATE OR REPLACE FUNCTION update_books_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
        
        trigger = """
        CREATE TRIGGER trigger_books_updated_at
            BEFORE UPDATE ON books
            FOR EACH ROW
            EXECUTE FUNCTION update_books_updated_at();
        """
        
        self.connection.execute_script(trigger_function)
        self.connection.execute_command(trigger)
    
    def _create_functions(self):
        """Create utility functions for book management"""
        
        # Function to update shelf count when books change
        shelf_count_function = """
        CREATE OR REPLACE FUNCTION update_shelf_count_on_book_change()
        RETURNS TRIGGER AS $$
        BEGIN
            -- Handle INSERT
            IF TG_OP = 'INSERT' THEN
                IF NEW.shelf_id IS NOT NULL AND NEW.book_type = 'physical' THEN
                    PERFORM update_shelf_book_count(NEW.shelf_id, 1);
                END IF;
                RETURN NEW;
            END IF;
            
            -- Handle UPDATE
            IF TG_OP = 'UPDATE' THEN
                -- If shelf changed for physical book
                IF OLD.shelf_id IS DISTINCT FROM NEW.shelf_id AND NEW.book_type = 'physical' THEN
                    -- Remove from old shelf
                    IF OLD.shelf_id IS NOT NULL THEN
                        PERFORM update_shelf_book_count(OLD.shelf_id, -1);
                    END IF;
                    -- Add to new shelf
                    IF NEW.shelf_id IS NOT NULL THEN
                        PERFORM update_shelf_book_count(NEW.shelf_id, 1);
                    END IF;
                END IF;
                
                -- If book type changed
                IF OLD.book_type IS DISTINCT FROM NEW.book_type THEN
                    IF OLD.book_type = 'physical' AND OLD.shelf_id IS NOT NULL THEN
                        PERFORM update_shelf_book_count(OLD.shelf_id, -1);
                    END IF;
                    IF NEW.book_type = 'physical' AND NEW.shelf_id IS NOT NULL THEN
                        PERFORM update_shelf_book_count(NEW.shelf_id, 1);
                    END IF;
                END IF;
                
                RETURN NEW;
            END IF;
            
            -- Handle DELETE
            IF TG_OP = 'DELETE' THEN
                IF OLD.shelf_id IS NOT NULL AND OLD.book_type = 'physical' THEN
                    PERFORM update_shelf_book_count(OLD.shelf_id, -1);
                END IF;
                RETURN OLD;
            END IF;
            
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
        """
        
        shelf_count_trigger = """
        CREATE TRIGGER trigger_books_shelf_count
            AFTER INSERT OR UPDATE OR DELETE ON books
            FOR EACH ROW
            EXECUTE FUNCTION update_shelf_count_on_book_change();
        """
        
        # Function to validate shelf placement
        validation_function = """
        CREATE OR REPLACE FUNCTION validate_book_shelf_placement()
        RETURNS TRIGGER AS $$
        BEGIN
            -- Only validate for physical books with shelf assignment
            IF NEW.book_type = 'physical' AND NEW.shelf_id IS NOT NULL THEN
                -- Check if shelf exists and has capacity
                IF NOT check_shelf_capacity(NEW.shelf_id) THEN
                    RAISE EXCEPTION 'Shelf % is at full capacity', NEW.shelf_id;
                END IF;
            END IF;
            
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
        
        validation_trigger = """
        CREATE TRIGGER trigger_books_shelf_validation
            BEFORE INSERT OR UPDATE ON books
            FOR EACH ROW
            EXECUTE FUNCTION validate_book_shelf_placement();
        """
        
        self.connection.execute_script(shelf_count_function)
        self.connection.execute_command(shelf_count_trigger)
        self.connection.execute_script(validation_function)
        self.connection.execute_command(validation_trigger)
    
    def _create_views(self):
        """Create utility views for book management"""
        
        # Book inventory view
        inventory_view = """
        CREATE OR REPLACE VIEW book_inventory AS
        SELECT 
            b.book_id,
            b.isbn,
            b.title,
            b.author,
            b.publisher,
            b.publication_year,
            b.edition,
            b.language,
            b.pages,
            b.book_type,
            b.status,
            b.acquisition_date,
            s.location_code,
            s.section,
            s.main_topic as shelf_topic,
            s.material as shelf_material,
            CASE 
                WHEN b.book_type = 'digital' THEN 'Digital Collection'
                WHEN b.shelf_id IS NULL THEN 'Unassigned'
                ELSE CONCAT(s.section, ' - ', s.location_code)
            END as location,
            CASE 
                WHEN b.status = 'available' THEN 'Available'
                WHEN b.status = 'loaned' THEN 'On Loan'
                WHEN b.status = 'maintenance' THEN 'Under Maintenance'
                WHEN b.status = 'lost' THEN 'Lost'
            END as availability_status,
            b.created_at,
            b.updated_at
        FROM books b
        LEFT JOIN shelves s ON b.shelf_id = s.shelf_id;
        """
        
        # Available books view
        available_view = """
        CREATE OR REPLACE VIEW available_books AS
        SELECT *
        FROM book_inventory
        WHERE status = 'available';
        """
        
        # Books by shelf view
        shelf_view = """
        CREATE OR REPLACE VIEW books_by_shelf AS
        SELECT 
            s.shelf_id,
            s.location_code,
            s.section,
            s.main_topic,
            s.total_capacity,
            s.current_book_count,
            COUNT(b.book_id) as actual_book_count,
            ARRAY_AGG(
                CASE WHEN b.book_id IS NOT NULL 
                THEN json_build_object(
                    'book_id', b.book_id,
                    'title', b.title,
                    'author', b.author,
                    'status', b.status
                ) 
                END
            ) FILTER (WHERE b.book_id IS NOT NULL) as books
        FROM shelves s
        LEFT JOIN books b ON s.shelf_id = b.shelf_id AND b.book_type = 'physical'
        GROUP BY s.shelf_id, s.location_code, s.section, s.main_topic, s.total_capacity, s.current_book_count
        ORDER BY s.location_code;
        """
        
        self.connection.execute_script(inventory_view)
        self.connection.execute_script(available_view)
        self.connection.execute_script(shelf_view)
    
    def drop_table(self) -> bool:
        """Drop Books table and related objects"""
        try:
            # Drop in reverse order of dependencies
            self.connection.execute_command("DROP VIEW IF EXISTS books_by_shelf;")
            self.connection.execute_command("DROP VIEW IF EXISTS available_books;")
            self.connection.execute_command("DROP VIEW IF EXISTS book_inventory;")
            self.connection.execute_command("DROP FUNCTION IF EXISTS validate_book_shelf_placement();")
            self.connection.execute_command("DROP FUNCTION IF EXISTS update_shelf_count_on_book_change();")
            self.connection.execute_command("DROP TABLE IF EXISTS books;")
            return True
        except Exception as e:
            print(f"Error dropping Books table: {e}")
            return False
    
    def table_exists(self) -> bool:
        """Check if Books table exists"""
        return self.connection.table_exists('books')
    
    def validate_book_data(self, book_data: dict) -> list:
        """Validate book data before insertion"""
        errors = []
        
        # Required fields
        required_fields = ['title', 'author']
        for field in required_fields:
            if not book_data.get(field) or len(str(book_data[field]).strip()) == 0:
                errors.append(f"{field} is required and cannot be empty")
        
        # ISBN validation
        isbn = book_data.get('isbn')
        if isbn and not self._validate_isbn(isbn):
            errors.append("ISBN must be in valid format (10 or 13 digits, last digit can be X)")
        
        # Publication year validation
        publication_year = book_data.get('publication_year')
        if publication_year is not None:
            try:
                year = int(publication_year)
                current_year = 2024  # Could be dynamic
                if year < 1000 or year > current_year + 1:
                    errors.append(f"Publication year must be between 1000 and {current_year + 1}")
            except (ValueError, TypeError):
                errors.append("Publication year must be a valid integer")
        
        # Pages validation
        pages = book_data.get('pages')
        if pages is not None:
            try:
                page_count = int(pages)
                if page_count <= 0:
                    errors.append("Pages must be a positive integer")
            except (ValueError, TypeError):
                errors.append("Pages must be a valid integer")
        
        # Book type validation
        book_type = book_data.get('book_type', 'physical')
        if book_type not in ['physical', 'digital']:
            errors.append("Book type must be 'physical' or 'digital'")
        
        # Status validation
        status = book_data.get('status', 'available')
        if status not in ['available', 'loaned', 'maintenance', 'lost']:
            errors.append("Status must be 'available', 'loaned', 'maintenance', or 'lost'")
        
        # Shelf relationship validation
        shelf_id = book_data.get('shelf_id')
        if book_type == 'physical' and not shelf_id:
            errors.append("Physical books must be assigned to a shelf")
        elif book_type == 'digital' and shelf_id:
            errors.append("Digital books cannot be assigned to a shelf")
        
        # Acquisition date validation
        acquisition_date = book_data.get('acquisition_date')
        if acquisition_date:
            try:
                from datetime import datetime
                if isinstance(acquisition_date, str):
                    datetime.strptime(acquisition_date, '%Y-%m-%d')
                # Could add check for future dates
            except ValueError:
                errors.append("Acquisition date must be in YYYY-MM-DD format")
        
        return errors
    
    def _validate_isbn(self, isbn: str) -> bool:
        """Validate ISBN format"""
        # Remove hyphens and spaces
        clean_isbn = re.sub(r'[-\s]', '', isbn)
        
        # Check ISBN-10 or ISBN-13 format
        if len(clean_isbn) == 10:
            return re.match(r'^[0-9]{9}[0-9X]$', clean_isbn) is not None
        elif len(clean_isbn) == 13:
            return re.match(r'^97[89][0-9]{9}[0-9X]$', clean_isbn) is not None
        
        return False
    
    def get_book_inventory(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Get book inventory with optional filters"""
        try:
            base_query = "SELECT * FROM book_inventory"
            params = []
            where_clauses = []
            
            if filters:
                if filters.get('status'):
                    where_clauses.append("status = %s")
                    params.append(filters['status'])
                
                if filters.get('book_type'):
                    where_clauses.append("book_type = %s")
                    params.append(filters['book_type'])
                
                if filters.get('shelf_id'):
                    where_clauses.append("shelf_id = %s")
                    params.append(filters['shelf_id'])
                
                if filters.get('author'):
                    where_clauses.append("author ILIKE %s")
                    params.append(f"%{filters['author']}%")
                
                if filters.get('title'):
                    where_clauses.append("title ILIKE %s")
                    params.append(f"%{filters['title']}%")
            
            if where_clauses:
                base_query += " WHERE " + " AND ".join(where_clauses)
            
            base_query += " ORDER BY title, author"
            
            return self.connection.execute_query(base_query, tuple(params) if params else None)
        except Exception as e:
            print(f"Error getting book inventory: {e}")
            return []
    
    def get_available_books(self) -> List[Dict[str, Any]]:
        """Get all available books"""
        try:
            return self.connection.execute_query("SELECT * FROM available_books ORDER BY title, author")
        except Exception as e:
            print(f"Error getting available books: {e}")
            return []
    
    def get_books_by_shelf(self, shelf_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get books organized by shelf"""
        try:
            if shelf_id:
                query = "SELECT * FROM books_by_shelf WHERE shelf_id = %s"
                params = (shelf_id,)
            else:
                query = "SELECT * FROM books_by_shelf"
                params = None
            
            return self.connection.execute_query(query, params)
        except Exception as e:
            print(f"Error getting books by shelf: {e}")
            return []
    
    def search_books(self, search_term: str, search_fields: List[str] = None) -> List[Dict[str, Any]]:
        """Search books across multiple fields"""
        try:
            if not search_fields:
                search_fields = ['title', 'author', 'publisher', 'isbn']
            
            where_clauses = []
            params = []
            
            for field in search_fields:
                where_clauses.append(f"{field} ILIKE %s")
                params.append(f"%{search_term}%")
            
            query = f"""
            SELECT * FROM book_inventory 
            WHERE {' OR '.join(where_clauses)}
            ORDER BY title, author
            """
            
            return self.connection.execute_query(query, tuple(params))
        except Exception as e:
            print(f"Error searching books: {e}")
            return []
    
    def get_book_statistics(self) -> Dict[str, Any]:
        """Get book collection statistics"""
        try:
            query = """
            SELECT 
                COUNT(*) as total_books,
                COUNT(CASE WHEN book_type = 'physical' THEN 1 END) as physical_books,
                COUNT(CASE WHEN book_type = 'digital' THEN 1 END) as digital_books,
                COUNT(CASE WHEN status = 'available' THEN 1 END) as available_books,
                COUNT(CASE WHEN status = 'loaned' THEN 1 END) as loaned_books,
                COUNT(CASE WHEN status = 'maintenance' THEN 1 END) as maintenance_books,
                COUNT(CASE WHEN status = 'lost' THEN 1 END) as lost_books,
                COUNT(DISTINCT author) as unique_authors,
                COUNT(DISTINCT publisher) as unique_publishers,
                COUNT(DISTINCT language) as languages,
                AVG(publication_year) as avg_publication_year,
                MIN(publication_year) as oldest_book_year,
                MAX(publication_year) as newest_book_year
            FROM books
            """
            result = self.connection.execute_query(query)
            return result[0] if result else {}
        except Exception as e:
            print(f"Error getting book statistics: {e}")
            return {}
    
    def move_book_to_shelf(self, book_id: int, new_shelf_id: int) -> bool:
        """Move a book to a different shelf"""
        try:
            # This will trigger the shelf count update automatically
            query = "UPDATE books SET shelf_id = %s WHERE book_id = %s AND book_type = 'physical'"
            rows_affected = self.connection.execute_command(query, (new_shelf_id, book_id))
            return rows_affected > 0
        except Exception as e:
            print(f"Error moving book to shelf: {e}")
            return False
    
    def update_book_status(self, book_id: int, new_status: str) -> bool:
        """Update book status"""
        try:
            if new_status not in ['available', 'loaned', 'maintenance', 'lost']:
                return False
            
            query = "UPDATE books SET status = %s WHERE book_id = %s"
            rows_affected = self.connection.execute_command(query, (new_status, book_id))
            return rows_affected > 0
        except Exception as e:
            print(f"Error updating book status: {e}")
            return False