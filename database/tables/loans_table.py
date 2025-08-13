"""
Loans table creation and management for PostgreSQL
"""

from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any
from database.connection.database_connection import DatabaseConnection
from database.config.database_config import DatabaseType


class LoansTableManager:
    """Manages Loans table creation and operations for PostgreSQL"""
    
    def __init__(self, connection: DatabaseConnection):
        self.connection = connection
        if connection.config.db_type != DatabaseType.POSTGRESQL:
            raise ValueError("LoansTableManager only supports PostgreSQL")
    
    def create_table(self) -> bool:
        """Create Loans table with PostgreSQL-specific constraints"""
        
        try:
            return self._create_postgresql_table()
        except Exception as e:
            print(f"Error creating Loans table: {e}")
            return False
    
    def _create_postgresql_table(self) -> bool:
        """Create Loans table for PostgreSQL"""
        
        sql = """
        CREATE TABLE IF NOT EXISTS loans (
            loan_id SERIAL PRIMARY KEY,
            book_id INTEGER NOT NULL REFERENCES books(book_id) ON DELETE CASCADE ON UPDATE CASCADE,
            student_id INTEGER NOT NULL REFERENCES students(student_id) ON DELETE CASCADE ON UPDATE CASCADE,
            loan_date DATE NOT NULL DEFAULT CURRENT_DATE,
            estimated_return_date DATE NOT NULL,
            actual_return_date DATE,
            loan_status VARCHAR(20) DEFAULT 'active' CHECK (loan_status IN ('active', 'returned', 'overdue', 'lost')),
            renewal_count INTEGER DEFAULT 0,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            -- Constraints
            CONSTRAINT chk_loan_date_not_future CHECK (loan_date <= CURRENT_DATE),
            CONSTRAINT chk_estimated_return_after_loan CHECK (estimated_return_date > loan_date),
            CONSTRAINT chk_actual_return_after_loan CHECK (actual_return_date IS NULL OR actual_return_date >= loan_date),
            CONSTRAINT chk_renewal_count_positive CHECK (renewal_count >= 0),
            CONSTRAINT chk_returned_loan_has_return_date CHECK (loan_status != 'returned' OR actual_return_date IS NOT NULL),
            CONSTRAINT chk_active_loan_no_return_date CHECK (loan_status != 'active' OR actual_return_date IS NULL),
            CONSTRAINT chk_reasonable_loan_period CHECK (estimated_return_date <= loan_date + INTERVAL '365 days')
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
            "CREATE UNIQUE INDEX idx_loans_unique_active_book ON loans(book_id) WHERE loan_status IN ('active', 'overdue');",
            "CREATE INDEX IF NOT EXISTS idx_loans_book_id ON loans(book_id);",
            "CREATE INDEX IF NOT EXISTS idx_loans_student_id ON loans(student_id);",
            "CREATE INDEX IF NOT EXISTS idx_loans_loan_date ON loans(loan_date);",
            "CREATE INDEX IF NOT EXISTS idx_loans_estimated_return_date ON loans(estimated_return_date);",
            "CREATE INDEX IF NOT EXISTS idx_loans_actual_return_date ON loans(actual_return_date);",
            "CREATE INDEX IF NOT EXISTS idx_loans_loan_status ON loans(loan_status);",
            "CREATE INDEX IF NOT EXISTS idx_loans_overdue ON loans(estimated_return_date, loan_status) WHERE loan_status IN ('active', 'overdue');",
            "CREATE INDEX IF NOT EXISTS idx_loans_student_active ON loans(student_id, loan_status) WHERE loan_status IN ('active', 'overdue');"
        ]
        
        for index_sql in indexes:
            try:
                self.connection.execute_command(index_sql)
            except Exception as e:
                # Index might already exist
                print(f"Warning: Could not create index: {e}")
    
    def _create_triggers(self):
        """Create triggers for PostgreSQL"""
        # Update timestamp trigger
        trigger_function = """
        CREATE OR REPLACE FUNCTION update_loans_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
        
        trigger = """
        CREATE TRIGGER trigger_loans_updated_at
            BEFORE UPDATE ON loans
            FOR EACH ROW
            EXECUTE FUNCTION update_loans_updated_at();
        """
        
        self.connection.execute_script(trigger_function)
        self.connection.execute_command(trigger)
    
    def _create_functions(self):
        """Create utility functions for loan management"""
        
        # Function to calculate estimated return date
        return_date_function = """
        CREATE OR REPLACE FUNCTION calculate_estimated_return_date(loan_date_param DATE, book_type_param VARCHAR DEFAULT 'physical')
        RETURNS DATE AS $$
        DECLARE
            default_loan_days INTEGER := 14;
            digital_loan_days INTEGER := 7;
        BEGIN
            IF book_type_param = 'digital' THEN
                RETURN loan_date_param + digital_loan_days;
            ELSE
                RETURN loan_date_param + default_loan_days;
            END IF;
        END;
        $$ LANGUAGE plpgsql;
        """
        
        # Function to update book status on loan changes
        book_status_function = """
        CREATE OR REPLACE FUNCTION update_book_status_on_loan_change()
        RETURNS TRIGGER AS $$
        BEGIN
            -- Handle INSERT (new loan)
            IF TG_OP = 'INSERT' THEN
                UPDATE books 
                SET status = 'loaned' 
                WHERE book_id = NEW.book_id;
                RETURN NEW;
            END IF;
            
            -- Handle UPDATE
            IF TG_OP = 'UPDATE' THEN
                -- If loan status changed to returned
                IF OLD.loan_status != 'returned' AND NEW.loan_status = 'returned' THEN
                    UPDATE books 
                    SET status = 'available' 
                    WHERE book_id = NEW.book_id;
                END IF;
                
                -- If loan status changed from returned to active/overdue
                IF OLD.loan_status = 'returned' AND NEW.loan_status IN ('active', 'overdue') THEN
                    UPDATE books 
                    SET status = 'loaned' 
                    WHERE book_id = NEW.book_id;
                END IF;
                
                -- If loan status changed to lost
                IF OLD.loan_status != 'lost' AND NEW.loan_status = 'lost' THEN
                    UPDATE books 
                    SET status = 'lost' 
                    WHERE book_id = NEW.book_id;
                END IF;
                
                RETURN NEW;
            END IF;
            
            -- Handle DELETE
            IF TG_OP = 'DELETE' THEN
                -- Only update book status if the loan was active
                IF OLD.loan_status IN ('active', 'overdue') THEN
                    UPDATE books 
                    SET status = 'available' 
                    WHERE book_id = OLD.book_id;
                END IF;
                RETURN OLD;
            END IF;
            
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
        """
        
        book_status_trigger = """
        CREATE TRIGGER trigger_loans_book_status
            AFTER INSERT OR UPDATE OR DELETE ON loans
            FOR EACH ROW
            EXECUTE FUNCTION update_book_status_on_loan_change();
        """
        
        # Function to update overdue loans
        overdue_function = """
        CREATE OR REPLACE FUNCTION update_overdue_loans()
        RETURNS INTEGER AS $$
        DECLARE
            updated_count INTEGER;
        BEGIN
            UPDATE loans 
            SET loan_status = 'overdue'
            WHERE loan_status = 'active' 
              AND actual_return_date IS NULL 
              AND estimated_return_date < CURRENT_DATE;
            
            GET DIAGNOSTICS updated_count = ROW_COUNT;
            RETURN updated_count;
        END;
        $$ LANGUAGE plpgsql;
        """
        
        # Function to validate loan creation
        validation_function = """
        CREATE OR REPLACE FUNCTION validate_loan_creation()
        RETURNS TRIGGER AS $$
        DECLARE
            book_status VARCHAR(20);
            book_type VARCHAR(20);
            student_status VARCHAR(20);
            active_loans_count INTEGER;
            max_loans INTEGER := 5; -- Default maximum loans per student
        BEGIN
            -- Check if book exists and is available
            SELECT status, book_type INTO book_status, book_type
            FROM books 
            WHERE book_id = NEW.book_id;
            
            IF NOT FOUND THEN
                RAISE EXCEPTION 'Book with ID % not found', NEW.book_id;
            END IF;
            
            IF book_status != 'available' THEN
                RAISE EXCEPTION 'Book % is not available for loan (status: %)', NEW.book_id, book_status;
            END IF;
            
            -- Check if student exists and is active
            SELECT status INTO student_status
            FROM students 
            WHERE student_id = NEW.student_id;
            
            IF NOT FOUND THEN
                RAISE EXCEPTION 'Student with ID % not found', NEW.student_id;
            END IF;
            
            IF student_status != 'active' THEN
                RAISE EXCEPTION 'Student % is not active (status: %)', NEW.student_id, student_status;
            END IF;
            
            -- Check student loan limit
            SELECT COUNT(*) INTO active_loans_count
            FROM loans 
            WHERE student_id = NEW.student_id 
              AND loan_status IN ('active', 'overdue');
            
            IF active_loans_count >= max_loans THEN
                RAISE EXCEPTION 'Student % has reached maximum loan limit (%)', NEW.student_id, max_loans;
            END IF;
            
            -- Set estimated return date if not provided
            IF NEW.estimated_return_date IS NULL THEN
                NEW.estimated_return_date := calculate_estimated_return_date(NEW.loan_date, book_type);
            END IF;
            
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
        
        validation_trigger = """
        CREATE TRIGGER trigger_loans_validation
            BEFORE INSERT ON loans
            FOR EACH ROW
            EXECUTE FUNCTION validate_loan_creation();
        """
        
        self.connection.execute_script(return_date_function)
        self.connection.execute_script(book_status_function)
        self.connection.execute_command(book_status_trigger)
        self.connection.execute_script(overdue_function)
        self.connection.execute_script(validation_function)
        self.connection.execute_command(validation_trigger)
    
    def _create_views(self):
        """Create utility views for loan management"""
        
        # Active loans view
        active_loans_view = """
        CREATE OR REPLACE VIEW active_loans AS
        SELECT 
            l.loan_id,
            l.loan_date,
            l.estimated_return_date,
            l.actual_return_date,
            l.loan_status,
            l.renewal_count,
            l.notes,
            b.book_id,
            b.title as book_title,
            b.author as book_author,
            b.isbn,
            b.book_type,
            s.student_id,
            s.student_number,
            s.first_name,
            s.last_name,
            s.email,
            s.program,
            CASE 
                WHEN l.loan_status = 'overdue' THEN CURRENT_DATE - l.estimated_return_date
                WHEN l.loan_status = 'active' AND l.estimated_return_date < CURRENT_DATE THEN CURRENT_DATE - l.estimated_return_date
                ELSE 0
            END as days_overdue,
            l.estimated_return_date - CURRENT_DATE as days_until_due,
            l.created_at,
            l.updated_at
        FROM loans l
        JOIN books b ON l.book_id = b.book_id
        JOIN students s ON l.student_id = s.student_id
        WHERE l.loan_status IN ('active', 'overdue');
        """
        
        # Overdue loans view
        overdue_loans_view = """
        CREATE OR REPLACE VIEW overdue_loans AS
        SELECT *
        FROM active_loans
        WHERE loan_status = 'overdue' OR (loan_status = 'active' AND estimated_return_date < CURRENT_DATE);
        """
        
        # Loan history view
        loan_history_view = """
        CREATE OR REPLACE VIEW loan_history AS
        SELECT 
            l.loan_id,
            l.loan_date,
            l.estimated_return_date,
            l.actual_return_date,
            l.loan_status,
            l.renewal_count,
            CASE 
                WHEN l.actual_return_date IS NOT NULL THEN l.actual_return_date - l.loan_date
                ELSE CURRENT_DATE - l.loan_date
            END as loan_duration,
            CASE 
                WHEN l.actual_return_date IS NOT NULL AND l.actual_return_date > l.estimated_return_date 
                THEN l.actual_return_date - l.estimated_return_date
                ELSE 0
            END as days_late,
            b.title as book_title,
            b.author as book_author,
            b.isbn,
            s.student_number,
            s.first_name,
            s.last_name,
            s.email,
            l.created_at,
            l.updated_at
        FROM loans l
        JOIN books b ON l.book_id = b.book_id
        JOIN students s ON l.student_id = s.student_id
        ORDER BY l.loan_date DESC;
        """
        
        self.connection.execute_script(active_loans_view)
        self.connection.execute_script(overdue_loans_view)
        self.connection.execute_script(loan_history_view)
    
    def drop_table(self) -> bool:
        """Drop Loans table and related objects"""
        try:
            # Drop in reverse order of dependencies
            self.connection.execute_command("DROP VIEW IF EXISTS loan_history;")
            self.connection.execute_command("DROP VIEW IF EXISTS overdue_loans;")
            self.connection.execute_command("DROP VIEW IF EXISTS active_loans;")
            self.connection.execute_command("DROP FUNCTION IF EXISTS validate_loan_creation();")
            self.connection.execute_command("DROP FUNCTION IF EXISTS update_overdue_loans();")
            self.connection.execute_command("DROP FUNCTION IF EXISTS update_book_status_on_loan_change();")
            self.connection.execute_command("DROP FUNCTION IF EXISTS calculate_estimated_return_date(DATE, VARCHAR);")
            self.connection.execute_command("DROP TABLE IF EXISTS loans;")
            return True
        except Exception as e:
            print(f"Error dropping Loans table: {e}")
            return False
    
    def table_exists(self) -> bool:
        """Check if Loans table exists"""
        return self.connection.table_exists('loans')
    
    def validate_loan_data(self, loan_data: dict) -> list:
        """Validate loan data before insertion"""
        errors = []
        
        # Required fields
        required_fields = ['book_id', 'student_id']
        for field in required_fields:
            if not loan_data.get(field):
                errors.append(f"{field} is required")
        
        # Loan date validation
        loan_date = loan_data.get('loan_date')
        if loan_date:
            try:
                if isinstance(loan_date, str):
                    loan_date = datetime.strptime(loan_date, '%Y-%m-%d').date()
                elif isinstance(loan_date, datetime):
                    loan_date = loan_date.date()
                
                if loan_date > date.today():
                    errors.append("Loan date cannot be in the future")
            except (ValueError, TypeError):
                errors.append("Loan date must be in YYYY-MM-DD format")
        
        # Estimated return date validation
        estimated_return_date = loan_data.get('estimated_return_date')
        if estimated_return_date:
            try:
                if isinstance(estimated_return_date, str):
                    estimated_return_date = datetime.strptime(estimated_return_date, '%Y-%m-%d').date()
                elif isinstance(estimated_return_date, datetime):
                    estimated_return_date = estimated_return_date.date()
                
                if loan_date and estimated_return_date <= loan_date:
                    errors.append("Estimated return date must be after loan date")
                
                # Check for reasonable loan period (max 1 year)
                if loan_date and (estimated_return_date - loan_date).days > 365:
                    errors.append("Loan period cannot exceed 365 days")
                    
            except (ValueError, TypeError):
                errors.append("Estimated return date must be in YYYY-MM-DD format")
        
        # Actual return date validation
        actual_return_date = loan_data.get('actual_return_date')
        if actual_return_date:
            try:
                if isinstance(actual_return_date, str):
                    actual_return_date = datetime.strptime(actual_return_date, '%Y-%m-%d').date()
                elif isinstance(actual_return_date, datetime):
                    actual_return_date = actual_return_date.date()
                
                if loan_date and actual_return_date < loan_date:
                    errors.append("Actual return date cannot be before loan date")
                    
            except (ValueError, TypeError):
                errors.append("Actual return date must be in YYYY-MM-DD format")
        
        # Loan status validation
        loan_status = loan_data.get('loan_status', 'active')
        if loan_status not in ['active', 'returned', 'overdue', 'lost']:
            errors.append("Loan status must be 'active', 'returned', 'overdue', or 'lost'")
        
        # Status-specific validations
        if loan_status == 'returned' and not actual_return_date:
            errors.append("Returned loans must have an actual return date")
        
        if loan_status == 'active' and actual_return_date:
            errors.append("Active loans cannot have an actual return date")
        
        # Renewal count validation
        renewal_count = loan_data.get('renewal_count', 0)
        if renewal_count is not None:
            try:
                count = int(renewal_count)
                if count < 0:
                    errors.append("Renewal count cannot be negative")
            except (ValueError, TypeError):
                errors.append("Renewal count must be a valid integer")
        
        return errors
    
    def create_loan(self, book_id: int, student_id: int, loan_date: Optional[date] = None, 
                   estimated_return_date: Optional[date] = None, notes: Optional[str] = None) -> Optional[int]:
        """Create a new loan"""
        try:
            if loan_date is None:
                loan_date = date.today()
            
            loan_data = {
                'book_id': book_id,
                'student_id': student_id,
                'loan_date': loan_date,
                'estimated_return_date': estimated_return_date,
                'notes': notes
            }
            
            # Validate data
            errors = self.validate_loan_data(loan_data)
            if errors:
                print(f"Validation errors: {errors}")
                return None
            
            # Insert loan (triggers will handle validation and book status update)
            if estimated_return_date:
                query = """
                INSERT INTO loans (book_id, student_id, loan_date, estimated_return_date, notes)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING loan_id
                """
                params = (book_id, student_id, loan_date, estimated_return_date, notes)
            else:
                query = """
                INSERT INTO loans (book_id, student_id, loan_date, notes)
                VALUES (%s, %s, %s, %s)
                RETURNING loan_id
                """
                params = (book_id, student_id, loan_date, notes)
            
            result = self.connection.execute_query(query, params)
            return result[0]['loan_id'] if result else None
            
        except Exception as e:
            print(f"Error creating loan: {e}")
            return None
    
    def return_book(self, loan_id: int, return_date: Optional[date] = None) -> bool:
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
    
    def get_active_loans(self, student_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get active loans"""
        try:
            if student_id:
                query = "SELECT * FROM active_loans WHERE student_id = %s ORDER BY estimated_return_date"
                params = (student_id,)
            else:
                query = "SELECT * FROM active_loans ORDER BY estimated_return_date"
                params = None
            
            return self.connection.execute_query(query, params)
        except Exception as e:
            print(f"Error getting active loans: {e}")
            return []
    
    def get_overdue_loans(self) -> List[Dict[str, Any]]:
        """Get overdue loans"""
        try:
            return self.connection.execute_query("SELECT * FROM overdue_loans ORDER BY days_overdue DESC")
        except Exception as e:
            print(f"Error getting overdue loans: {e}")
            return []
    
    def get_loan_history(self, student_id: Optional[int] = None, book_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get loan history"""
        try:
            base_query = "SELECT * FROM loan_history"
            params = []
            where_clauses = []
            
            if student_id:
                where_clauses.append("student_id = %s")
                params.append(student_id)
            
            if book_id:
                where_clauses.append("book_id = %s")
                params.append(book_id)
            
            if where_clauses:
                base_query += " WHERE " + " AND ".join(where_clauses)
            
            return self.connection.execute_query(base_query, tuple(params) if params else None)
        except Exception as e:
            print(f"Error getting loan history: {e}")
            return []
    
    def update_overdue_loans(self) -> int:
        """Update loans that are past due to overdue status"""
        try:
            result = self.connection.execute_query("SELECT update_overdue_loans() as updated_count")
            return result[0]['updated_count'] if result else 0
        except Exception as e:
            print(f"Error updating overdue loans: {e}")
            return 0
    
    def get_loan_statistics(self) -> Dict[str, Any]:
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
                COUNT(CASE WHEN actual_return_date > estimated_return_date THEN 1 END) as late_returns,
                AVG(renewal_count) as avg_renewals
            FROM loans
            """
            result = self.connection.execute_query(query)
            return result[0] if result else {}
        except Exception as e:
            print(f"Error getting loan statistics: {e}")
            return {}
    
    def get_student_loan_summary(self, student_id: int) -> Dict[str, Any]:
        """Get loan summary for a specific student"""
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