-- Description: Create Loans table with date validation
-- Version: 20241208_150000
-- Created: 2024-12-08T15:00:00

-- UP
-- Create Loans table with comprehensive date validation and loan management

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

-- Create unique constraint to prevent multiple active loans for the same book
CREATE UNIQUE INDEX idx_loans_unique_active_book 
ON loans(book_id) 
WHERE loan_status IN ('active', 'overdue');

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_loans_book_id ON loans(book_id);
CREATE INDEX IF NOT EXISTS idx_loans_student_id ON loans(student_id);
CREATE INDEX IF NOT EXISTS idx_loans_loan_date ON loans(loan_date);
CREATE INDEX IF NOT EXISTS idx_loans_estimated_return_date ON loans(estimated_return_date);
CREATE INDEX IF NOT EXISTS idx_loans_actual_return_date ON loans(actual_return_date);
CREATE INDEX IF NOT EXISTS idx_loans_loan_status ON loans(loan_status);
CREATE INDEX IF NOT EXISTS idx_loans_overdue ON loans(estimated_return_date, loan_status) WHERE loan_status IN ('active', 'overdue');
CREATE INDEX IF NOT EXISTS idx_loans_student_active ON loans(student_id, loan_status) WHERE loan_status IN ('active', 'overdue');

-- Create trigger for updating updated_at timestamp
CREATE OR REPLACE FUNCTION update_loans_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_loans_updated_at
    BEFORE UPDATE ON loans
    FOR EACH ROW
    EXECUTE FUNCTION update_loans_updated_at();

-- Create function to calculate estimated return date based on loan policies
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

-- Create trigger to update book status when loan status changes
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

CREATE TRIGGER trigger_loans_book_status
    AFTER INSERT OR UPDATE OR DELETE ON loans
    FOR EACH ROW
    EXECUTE FUNCTION update_book_status_on_loan_change();

-- Create function to automatically update overdue loans
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

-- Create function to validate loan creation
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

CREATE TRIGGER trigger_loans_validation
    BEFORE INSERT ON loans
    FOR EACH ROW
    EXECUTE FUNCTION validate_loan_creation();

-- Create view for active loans with book and student information
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

-- Create view for overdue loans
CREATE OR REPLACE VIEW overdue_loans AS
SELECT *
FROM active_loans
WHERE loan_status = 'overdue' OR (loan_status = 'active' AND estimated_return_date < CURRENT_DATE);

-- Create view for loan history
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

-- Create audit trigger for loans table
CREATE TRIGGER trigger_loans_audit
    AFTER INSERT OR UPDATE OR DELETE ON loans
    FOR EACH ROW
    EXECUTE FUNCTION audit_trigger_function();

-- Add comments for documentation
COMMENT ON TABLE loans IS 'Loan transactions with date validation and status tracking';
COMMENT ON COLUMN loans.loan_id IS 'Primary key, auto-incrementing loan ID';
COMMENT ON COLUMN loans.book_id IS 'Foreign key to books table';
COMMENT ON COLUMN loans.student_id IS 'Foreign key to students table';
COMMENT ON COLUMN loans.loan_date IS 'Date when book was loaned';
COMMENT ON COLUMN loans.estimated_return_date IS 'Expected return date';
COMMENT ON COLUMN loans.actual_return_date IS 'Actual return date (NULL if not returned)';
COMMENT ON COLUMN loans.loan_status IS 'Current status: active, returned, overdue, lost';
COMMENT ON COLUMN loans.renewal_count IS 'Number of times loan has been renewed';
COMMENT ON COLUMN loans.notes IS 'Additional notes about the loan';

COMMENT ON FUNCTION calculate_estimated_return_date(DATE, VARCHAR) IS 'Calculate estimated return date based on loan policies';
COMMENT ON FUNCTION update_overdue_loans() IS 'Update loans that are past due date to overdue status';
COMMENT ON FUNCTION validate_loan_creation() IS 'Validate loan creation business rules';
COMMENT ON VIEW active_loans IS 'Currently active and overdue loans with full details';
COMMENT ON VIEW overdue_loans IS 'Loans that are past their due date';
COMMENT ON VIEW loan_history IS 'Complete loan history with duration and late calculations';

-- DOWN
-- Remove audit trigger
DROP TRIGGER IF EXISTS trigger_loans_audit ON loans;

-- Remove views
DROP VIEW IF EXISTS loan_history;
DROP VIEW IF EXISTS overdue_loans;
DROP VIEW IF EXISTS active_loans;

-- Remove triggers and functions
DROP TRIGGER IF EXISTS trigger_loans_validation ON loans;
DROP FUNCTION IF EXISTS validate_loan_creation();

DROP TRIGGER IF EXISTS trigger_loans_book_status ON loans;
DROP FUNCTION IF EXISTS update_book_status_on_loan_change();

DROP FUNCTION IF EXISTS update_overdue_loans();
DROP FUNCTION IF EXISTS calculate_estimated_return_date(DATE, VARCHAR);

DROP TRIGGER IF EXISTS trigger_loans_updated_at ON loans;
DROP FUNCTION IF EXISTS update_loans_updated_at();

-- Remove indexes
DROP INDEX IF EXISTS idx_loans_student_active;
DROP INDEX IF EXISTS idx_loans_overdue;
DROP INDEX IF EXISTS idx_loans_loan_status;
DROP INDEX IF EXISTS idx_loans_actual_return_date;
DROP INDEX IF EXISTS idx_loans_estimated_return_date;
DROP INDEX IF EXISTS idx_loans_loan_date;
DROP INDEX IF EXISTS idx_loans_student_id;
DROP INDEX IF EXISTS idx_loans_book_id;
DROP INDEX IF EXISTS idx_loans_unique_active_book;

-- Drop table
DROP TABLE IF EXISTS loans;