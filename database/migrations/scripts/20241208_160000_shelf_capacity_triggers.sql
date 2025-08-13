-- Description: Create shelf capacity enforcement triggers
-- Version: 20241208_160000
-- Created: 2024-12-08T16:00:00

-- UP
-- Create triggers to enforce shelf capacity limits

-- Function to check and enforce shelf capacity
CREATE OR REPLACE FUNCTION enforce_shelf_capacity()
RETURNS TRIGGER AS $$
DECLARE
    current_count INTEGER;
    max_capacity INTEGER;
BEGIN
    -- Only check for physical books being assigned to shelves
    IF NEW.book_type = 'physical' AND NEW.shelf_id IS NOT NULL THEN
        SELECT current_book_count, total_capacity
        INTO current_count, max_capacity
        FROM shelves
        WHERE shelf_id = NEW.shelf_id;
        
        IF NOT FOUND THEN
            RAISE EXCEPTION 'Shelf % does not exist', NEW.shelf_id;
        END IF;
        
        -- For INSERT, check if adding this book would exceed capacity
        IF TG_OP = 'INSERT' THEN
            IF current_count >= max_capacity THEN
                RAISE EXCEPTION 'Shelf % is at full capacity (% / %)', NEW.shelf_id, current_count, max_capacity;
            END IF;
        END IF;
        
        -- For UPDATE, check if moving to new shelf would exceed capacity
        IF TG_OP = 'UPDATE' AND OLD.shelf_id IS DISTINCT FROM NEW.shelf_id THEN
            IF current_count >= max_capacity THEN
                RAISE EXCEPTION 'Shelf % is at full capacity (% / %)', NEW.shelf_id, current_count, max_capacity;
            END IF;
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to enforce capacity before book placement
CREATE TRIGGER trigger_enforce_shelf_capacity
    BEFORE INSERT OR UPDATE ON books
    FOR EACH ROW
    EXECUTE FUNCTION enforce_shelf_capacity();

-- Function to update shelf counts automatically
CREATE OR REPLACE FUNCTION auto_update_shelf_counts()
RETURNS TRIGGER AS $$
BEGIN
    -- Handle INSERT
    IF TG_OP = 'INSERT' THEN
        IF NEW.shelf_id IS NOT NULL AND NEW.book_type = 'physical' THEN
            UPDATE shelves 
            SET current_book_count = current_book_count + 1
            WHERE shelf_id = NEW.shelf_id;
        END IF;
        RETURN NEW;
    END IF;
    
    -- Handle UPDATE
    IF TG_OP = 'UPDATE' THEN
        -- If shelf changed for physical book
        IF OLD.shelf_id IS DISTINCT FROM NEW.shelf_id AND NEW.book_type = 'physical' THEN
            -- Remove from old shelf
            IF OLD.shelf_id IS NOT NULL THEN
                UPDATE shelves 
                SET current_book_count = current_book_count - 1
                WHERE shelf_id = OLD.shelf_id;
            END IF;
            -- Add to new shelf
            IF NEW.shelf_id IS NOT NULL THEN
                UPDATE shelves 
                SET current_book_count = current_book_count + 1
                WHERE shelf_id = NEW.shelf_id;
            END IF;
        END IF;
        
        -- If book type changed
        IF OLD.book_type IS DISTINCT FROM NEW.book_type THEN
            IF OLD.book_type = 'physical' AND OLD.shelf_id IS NOT NULL THEN
                UPDATE shelves 
                SET current_book_count = current_book_count - 1
                WHERE shelf_id = OLD.shelf_id;
            END IF;
            IF NEW.book_type = 'physical' AND NEW.shelf_id IS NOT NULL THEN
                UPDATE shelves 
                SET current_book_count = current_book_count + 1
                WHERE shelf_id = NEW.shelf_id;
            END IF;
        END IF;
        
        RETURN NEW;
    END IF;
    
    -- Handle DELETE
    IF TG_OP = 'DELETE' THEN
        IF OLD.shelf_id IS NOT NULL AND OLD.book_type = 'physical' THEN
            UPDATE shelves 
            SET current_book_count = current_book_count - 1
            WHERE shelf_id = OLD.shelf_id;
        END IF;
        RETURN OLD;
    END IF;
    
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to auto-update shelf counts
CREATE TRIGGER trigger_auto_update_shelf_counts
    AFTER INSERT OR UPDATE OR DELETE ON books
    FOR EACH ROW
    EXECUTE FUNCTION auto_update_shelf_counts();

-- Function to validate shelf capacity consistency
CREATE OR REPLACE FUNCTION validate_shelf_capacity_consistency()
RETURNS TABLE(shelf_id INTEGER, location_code VARCHAR, expected_count BIGINT, actual_count INTEGER, status TEXT) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        s.shelf_id,
        s.location_code,
        COUNT(b.book_id) as expected_count,
        s.current_book_count as actual_count,
        CASE 
            WHEN COUNT(b.book_id) = s.current_book_count THEN 'OK'
            ELSE 'MISMATCH'
        END as status
    FROM shelves s
    LEFT JOIN books b ON s.shelf_id = b.shelf_id AND b.book_type = 'physical'
    GROUP BY s.shelf_id, s.location_code, s.current_book_count
    ORDER BY s.location_code;
END;
$$ LANGUAGE plpgsql;

-- DOWN
DROP TRIGGER IF EXISTS trigger_auto_update_shelf_counts ON books;
DROP FUNCTION IF EXISTS auto_update_shelf_counts();
DROP TRIGGER IF EXISTS trigger_enforce_shelf_capacity ON books;
DROP FUNCTION IF EXISTS enforce_shelf_capacity();
DROP FUNCTION IF EXISTS validate_shelf_capacity_consistency();