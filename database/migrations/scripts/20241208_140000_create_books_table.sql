-- Description: Create Books table with shelf relationships
-- Version: 20241208_140000
-- Created: 2024-12-08T14:00:00

-- UP
-- Create Books table with comprehensive shelf relationships and constraints

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

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_books_isbn ON books(isbn);
CREATE INDEX IF NOT EXISTS idx_books_title ON books(title);
CREATE INDEX IF NOT EXISTS idx_books_author ON books(author);
CREATE INDEX IF NOT EXISTS idx_books_publisher ON books(publisher);
CREATE INDEX IF NOT EXISTS idx_books_status ON books(status);
CREATE INDEX IF NOT EXISTS idx_books_book_type ON books(book_type);
CREATE INDEX IF NOT EXISTS idx_books_shelf_id ON books(shelf_id);
CREATE INDEX IF NOT EXISTS idx_books_publication_year ON books(publication_year);
CREATE INDEX IF NOT EXISTS idx_books_language ON books(language);
CREATE INDEX IF NOT EXISTS idx_books_title_author ON books(title, author);

-- Create trigger for updating updated_at timestamp
CREATE OR REPLACE FUNCTION update_books_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_books_updated_at
    BEFORE UPDATE ON books
    FOR EACH ROW
    EXECUTE FUNCTION update_books_updated_at();

-- Create trigger to update shelf book count when books are added/removed/moved
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

CREATE TRIGGER trigger_books_shelf_count
    AFTER INSERT OR UPDATE OR DELETE ON books
    FOR EACH ROW
    EXECUTE FUNCTION update_shelf_count_on_book_change();

-- Create function to validate book placement on shelf
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

CREATE TRIGGER trigger_books_shelf_validation
    BEFORE INSERT OR UPDATE ON books
    FOR EACH ROW
    EXECUTE FUNCTION validate_book_shelf_placement();

-- Create view for book inventory with shelf information
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

-- Create view for available books
CREATE OR REPLACE VIEW available_books AS
SELECT *
FROM book_inventory
WHERE status = 'available';

-- Create view for books by shelf
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

-- Create audit trigger for books table
CREATE TRIGGER trigger_books_audit
    AFTER INSERT OR UPDATE OR DELETE ON books
    FOR EACH ROW
    EXECUTE FUNCTION audit_trigger_function();

-- Add comments for documentation
COMMENT ON TABLE books IS 'Book inventory with shelf relationships and status tracking';
COMMENT ON COLUMN books.book_id IS 'Primary key, auto-incrementing book ID';
COMMENT ON COLUMN books.isbn IS 'International Standard Book Number (optional, unique)';
COMMENT ON COLUMN books.title IS 'Book title';
COMMENT ON COLUMN books.author IS 'Book author(s)';
COMMENT ON COLUMN books.publisher IS 'Publishing company';
COMMENT ON COLUMN books.publication_year IS 'Year of publication';
COMMENT ON COLUMN books.edition IS 'Book edition information';
COMMENT ON COLUMN books.language IS 'Primary language of the book';
COMMENT ON COLUMN books.pages IS 'Number of pages';
COMMENT ON COLUMN books.book_type IS 'Type: physical or digital';
COMMENT ON COLUMN books.shelf_id IS 'Foreign key to shelves table (for physical books)';
COMMENT ON COLUMN books.status IS 'Current status: available, loaned, maintenance, lost';
COMMENT ON COLUMN books.acquisition_date IS 'Date when book was acquired by library';

COMMENT ON FUNCTION validate_book_shelf_placement() IS 'Validates shelf capacity before book placement';
COMMENT ON FUNCTION update_shelf_count_on_book_change() IS 'Automatically updates shelf book counts';
COMMENT ON VIEW book_inventory IS 'Complete book inventory with shelf and location information';
COMMENT ON VIEW available_books IS 'Books currently available for loan';
COMMENT ON VIEW books_by_shelf IS 'Books organized by shelf with aggregated information';

-- DOWN
-- Remove audit trigger
DROP TRIGGER IF EXISTS trigger_books_audit ON books;

-- Remove views
DROP VIEW IF EXISTS books_by_shelf;
DROP VIEW IF EXISTS available_books;
DROP VIEW IF EXISTS book_inventory;

-- Remove triggers and functions
DROP TRIGGER IF EXISTS trigger_books_shelf_validation ON books;
DROP FUNCTION IF EXISTS validate_book_shelf_placement();

DROP TRIGGER IF EXISTS trigger_books_shelf_count ON books;
DROP FUNCTION IF EXISTS update_shelf_count_on_book_change();

DROP TRIGGER IF EXISTS trigger_books_updated_at ON books;
DROP FUNCTION IF EXISTS update_books_updated_at();

-- Remove indexes
DROP INDEX IF EXISTS idx_books_title_author;
DROP INDEX IF EXISTS idx_books_language;
DROP INDEX IF EXISTS idx_books_publication_year;
DROP INDEX IF EXISTS idx_books_shelf_id;
DROP INDEX IF EXISTS idx_books_book_type;
DROP INDEX IF EXISTS idx_books_status;
DROP INDEX IF EXISTS idx_books_publisher;
DROP INDEX IF EXISTS idx_books_author;
DROP INDEX IF EXISTS idx_books_title;
DROP INDEX IF EXISTS idx_books_isbn;

-- Drop table
DROP TABLE IF EXISTS books;