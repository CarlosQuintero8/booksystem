-- Description: Create Shelves table with capacity management
-- Version: 20241208_130000
-- Created: 2024-12-08T13:00:00

-- UP
-- Create Shelves table with comprehensive capacity management

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

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_shelves_location_code ON shelves(location_code);
CREATE INDEX IF NOT EXISTS idx_shelves_section ON shelves(section);
CREATE INDEX IF NOT EXISTS idx_shelves_main_topic ON shelves(main_topic);
CREATE INDEX IF NOT EXISTS idx_shelves_material ON shelves(material);
CREATE INDEX IF NOT EXISTS idx_shelves_capacity ON shelves(total_capacity, current_book_count);

-- Create trigger for updating updated_at timestamp
CREATE OR REPLACE FUNCTION update_shelves_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_shelves_updated_at
    BEFORE UPDATE ON shelves
    FOR EACH ROW
    EXECUTE FUNCTION update_shelves_updated_at();

-- Create function to check shelf capacity before adding books
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

-- Create function to update shelf book count
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

-- Create view for shelf utilization analysis
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

-- Create audit trigger for shelves table
CREATE TRIGGER trigger_shelves_audit
    AFTER INSERT OR UPDATE OR DELETE ON shelves
    FOR EACH ROW
    EXECUTE FUNCTION audit_trigger_function();

-- Add comments for documentation
COMMENT ON TABLE shelves IS 'Physical shelf organization and capacity management';
COMMENT ON COLUMN shelves.shelf_id IS 'Primary key, auto-incrementing shelf ID';
COMMENT ON COLUMN shelves.location_code IS 'Unique shelf location identifier (e.g., A1, B2, C10)';
COMMENT ON COLUMN shelves.section IS 'Library section name (e.g., Section A, Section B)';
COMMENT ON COLUMN shelves.main_topic IS 'Primary subject area for books on this shelf';
COMMENT ON COLUMN shelves.material IS 'Material the shelf is made of';
COMMENT ON COLUMN shelves.total_capacity IS 'Maximum number of books this shelf can hold';
COMMENT ON COLUMN shelves.current_book_count IS 'Current number of books on this shelf';
COMMENT ON FUNCTION check_shelf_capacity(INTEGER) IS 'Check if shelf has available capacity for more books';
COMMENT ON FUNCTION update_shelf_book_count(INTEGER, INTEGER) IS 'Update shelf book count with validation';
COMMENT ON VIEW shelf_utilization IS 'Shelf utilization analysis with status and percentages';

-- DOWN
-- Remove audit trigger
DROP TRIGGER IF EXISTS trigger_shelves_audit ON shelves;

-- Remove view
DROP VIEW IF EXISTS shelf_utilization;

-- Remove functions
DROP FUNCTION IF EXISTS update_shelf_book_count(INTEGER, INTEGER);
DROP FUNCTION IF EXISTS check_shelf_capacity(INTEGER);

-- Remove update trigger and function
DROP TRIGGER IF EXISTS trigger_shelves_updated_at ON shelves;
DROP FUNCTION IF EXISTS update_shelves_updated_at();

-- Remove indexes
DROP INDEX IF EXISTS idx_shelves_capacity;
DROP INDEX IF EXISTS idx_shelves_material;
DROP INDEX IF EXISTS idx_shelves_main_topic;
DROP INDEX IF EXISTS idx_shelves_section;
DROP INDEX IF EXISTS idx_shelves_location_code;

-- Drop table
DROP TABLE IF EXISTS shelves;