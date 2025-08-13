-- Description: Implement loan status management system
-- Version: 20241208_170000
-- Created: 2024-12-08T17:00:00

-- UP
-- Create loan status management triggers and functions

-- Function to prevent multiple active loans for same book
CREATE OR REPLACE FUNCTION prevent_duplicate_active_loans()
RETURNS TRIGGER AS $$
DECLARE
    existing_loan_count INTEGER;
BEGIN
    -- Check for existing active loans for this book
    SELECT COUNT(*) INTO existing_loan_count
    FROM loans 
    WHERE book_id = NEW.book_id 
      AND loan_status IN ('active', 'overdue')
      AND (TG_OP = 'INSERT' OR loan_id != NEW.loan_id);
    
    IF existing_loan_count > 0 THEN
        RAISE EXCEPTION 'Book % already has an active loan', NEW.book_id;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to prevent duplicate active loans
CREATE TRIGGER trigger_prevent_duplicate_active_loans
    BEFORE INSERT OR UPDATE ON loans
    FOR EACH ROW
    WHEN (NEW.loan_status IN ('active', 'overdue'))
    EXECUTE FUNCTION prevent_duplicate_active_loans();

-- Function to auto-update book status based on loan changes
CREATE OR REPLACE FUNCTION sync_book_loan_status()
RETURNS TRIGGER AS $$
BEGIN
    -- Handle INSERT (new loan)
    IF TG_OP = 'INSERT' THEN
        IF NEW.loan_status IN ('active', 'overdue') THEN
            UPDATE books SET status = 'loaned' WHERE book_id = NEW.book_id;
        END IF;
        RETURN NEW;
    END IF;
    
    -- Handle UPDATE
    IF TG_OP = 'UPDATE' THEN
        -- Loan returned
        IF OLD.loan_status IN ('active', 'overdue') AND NEW.loan_status = 'returned' THEN
            UPDATE books SET status = 'available' WHERE book_id = NEW.book_id;
        END IF;
        
        -- Loan reactivated
        IF OLD.loan_status = 'returned' AND NEW.loan_status IN ('active', 'overdue') THEN
            UPDATE books SET status = 'loaned' WHERE book_id = NEW.book_id;
        END IF;
        
        -- Book lost
        IF NEW.loan_status = 'lost' THEN
            UPDATE books SET status = 'lost' WHERE book_id = NEW.book_id;
        END IF;
        
        RETURN NEW;
    END IF;
    
    -- Handle DELETE
    IF TG_OP = 'DELETE' THEN
        IF OLD.loan_status IN ('active', 'overdue') THEN
            UPDATE books SET status = 'available' WHERE book_id = OLD.book_id;
        END IF;
        RETURN OLD;
    END IF;
    
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to sync book status
CREATE TRIGGER trigger_sync_book_loan_status
    AFTER INSERT OR UPDATE OR DELETE ON loans
    FOR EACH ROW
    EXECUTE FUNCTION sync_book_loan_status();

-- Function to batch update overdue loans
CREATE OR REPLACE FUNCTION batch_update_overdue_loans()
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
    
    INSERT INTO audit_log (table_name, operation, new_values, timestamp)
    VALUES ('loans', 'BATCH_UPDATE', 
            json_build_object('updated_count', updated_count, 'operation', 'mark_overdue'),
            CURRENT_TIMESTAMP);
    
    RETURN updated_count;
END;
$$ LANGUAGE plpgsql;

-- DOWN
DROP TRIGGER IF EXISTS trigger_sync_book_loan_status ON loans;
DROP FUNCTION IF EXISTS sync_book_loan_status();
DROP TRIGGER IF EXISTS trigger_prevent_duplicate_active_loans ON loans;
DROP FUNCTION IF EXISTS prevent_duplicate_active_loans();
DROP FUNCTION IF EXISTS batch_update_overdue_loans();