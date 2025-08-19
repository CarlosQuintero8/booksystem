-- =====================================================
-- LIBRARY MANAGEMENT SYSTEM - MANUAL TESTING QUERIES
-- Use these queries in pgAdmin for comprehensive testing
-- =====================================================

-- =====================================
-- 1. BASIC DATA VERIFICATION
-- =====================================

-- Check all tables and row counts
SELECT 'DATABASE OVERVIEW' as section;

SELECT 
    'students' as table_name, COUNT(*) as row_count FROM students
UNION ALL
SELECT 'books', COUNT(*) FROM books
UNION ALL
SELECT 'shelves', COUNT(*) FROM shelves
UNION ALL
SELECT 'loans', COUNT(*) FROM loans
ORDER BY table_name;

-- =====================================
-- 2. STUDENTS QUERIES
-- =====================================

SELECT 'STUDENTS SECTION' as section;

-- View all students
SELECT * FROM students ORDER BY student_number;

-- Students by program
SELECT 
    program,
    COUNT(*) as student_count
FROM students 
GROUP BY program
ORDER BY student_count DESC;

-- Students by enrollment year
SELECT 
    enrollment_year,
    COUNT(*) as student_count
FROM students 
WHERE enrollment_year IS NOT NULL
GROUP BY enrollment_year
ORDER BY enrollment_year DESC;

-- Search students by name
SELECT * FROM students 
WHERE first_name ILIKE '%juan%' OR last_name ILIKE '%pérez%';

-- Active students only
SELECT * FROM students WHERE status = 'active';

-- =====================================
-- 3. BOOKS QUERIES
-- =====================================

SELECT 'BOOKS SECTION' as section;

-- View all books with shelf information
SELECT 
    b.book_id,
    b.title,
    b.author,
    b.isbn,
    b.status,
    b.publication_year,
    s.location_code,
    s.section,
    s.main_topic
FROM books b
LEFT JOIN shelves s ON b.shelf_id = s.shelf_id
ORDER BY b.title;

-- Books by status
SELECT 
    status,
    COUNT(*) as book_count
FROM books
GROUP BY status
ORDER BY book_count DESC;

-- Available books (using the view)
SELECT * FROM available_books ORDER BY title;

-- Search books by title
SELECT * FROM books 
WHERE title ILIKE '%java%' OR title ILIKE '%algorithm%'
ORDER BY title;

-- Search books by author
SELECT * FROM books 
WHERE author ILIKE '%martin%' OR author ILIKE '%bloch%'
ORDER BY author;

-- Books by publication year
SELECT 
    publication_year,
    COUNT(*) as book_count
FROM books
WHERE publication_year IS NOT NULL
GROUP BY publication_year
ORDER BY publication_year DESC;

-- Books by language
SELECT 
    language,
    COUNT(*) as book_count
FROM books
GROUP BY language
ORDER BY book_count DESC;

-- Books by shelf/section
SELECT 
    s.section,
    s.location_code,
    COUNT(b.book_id) as book_count
FROM shelves s
LEFT JOIN books b ON s.shelf_id = b.shelf_id
GROUP BY s.section, s.location_code, s.shelf_id
ORDER BY s.section, s.location_code;

-- =====================================
-- 4. SHELVES QUERIES
-- =====================================

SELECT 'SHELVES SECTION' as section;

-- View all shelves with utilization
SELECT 
    location_code,
    section,
    main_topic,
    material,
    total_capacity,
    current_book_count,
    ROUND((current_book_count::decimal / total_capacity * 100), 2) as utilization_percent,
    (total_capacity - current_book_count) as available_space
FROM shelves
ORDER BY utilization_percent DESC;

-- Shelves by section
SELECT 
    section,
    COUNT(*) as shelf_count,
    SUM(total_capacity) as total_capacity,
    SUM(current_book_count) as total_books,
    ROUND(AVG(current_book_count::decimal / total_capacity * 100), 2) as avg_utilization
FROM shelves
GROUP BY section
ORDER BY section;

-- Find shelves with available space
SELECT 
    location_code,
    section,
    main_topic,
    total_capacity,
    current_book_count,
    (total_capacity - current_book_count) as available_space
FROM shelves
WHERE current_book_count < total_capacity
ORDER BY available_space DESC;

-- Most utilized shelves
SELECT 
    location_code,
    section,
    main_topic,
    ROUND((current_book_count::decimal / total_capacity * 100), 2) as utilization_percent
FROM shelves
WHERE total_capacity > 0
ORDER BY utilization_percent DESC;

-- Empty shelves
SELECT * FROM shelves WHERE current_book_count = 0;

-- Full shelves
SELECT * FROM shelves WHERE current_book_count = total_capacity;

-- =====================================
-- 5. LOANS QUERIES
-- =====================================

SELECT 'LOANS SECTION' as section;

-- View all loans with details
SELECT 
    l.loan_id,
    s.student_number,
    s.first_name || ' ' || s.last_name as student_name,
    b.title as book_title,
    b.author,
    l.loan_date,
    l.expected_return_date,
    l.actual_return_date,
    l.status,
    l.renewal_count,
    CASE 
        WHEN l.actual_return_date IS NOT NULL THEN l.actual_return_date - l.loan_date
        ELSE CURRENT_DATE - l.loan_date
    END as days_on_loan
FROM loans l
JOIN students s ON l.student_id = s.student_id
JOIN books b ON l.book_id = b.book_id
ORDER BY l.loan_date DESC;

-- Active loans only
SELECT 
    s.student_number,
    s.first_name || ' ' || s.last_name as student_name,
    b.title,
    b.author,
    l.loan_date,
    l.expected_return_date,
    CURRENT_DATE - l.expected_return_date as days_overdue,
    CASE 
        WHEN l.expected_return_date < CURRENT_DATE THEN 'OVERDUE'
        ELSE 'ON TIME'
    END as status
FROM loans l
JOIN students s ON l.student_id = s.student_id
JOIN books b ON l.book_id = b.book_id
WHERE l.status = 'active'
ORDER BY l.expected_return_date;

-- Overdue loans (using the view)
SELECT * FROM overdue_loans ORDER BY days_overdue DESC;

-- Loans by status
SELECT 
    status,
    COUNT(*) as loan_count
FROM loans
GROUP BY status
ORDER BY loan_count DESC;

-- Loans by month
SELECT 
    DATE_TRUNC('month', loan_date) as month,
    COUNT(*) as loans_created,
    COUNT(CASE WHEN status = 'returned' THEN 1 END) as loans_returned,
    COUNT(CASE WHEN status = 'active' THEN 1 END) as loans_active,
    COUNT(CASE WHEN status = 'overdue' THEN 1 END) as loans_overdue
FROM loans
GROUP BY DATE_TRUNC('month', loan_date)
ORDER BY month DESC;

-- Student loan history
SELECT 
    s.student_number,
    s.first_name || ' ' || s.last_name as student_name,
    COUNT(l.loan_id) as total_loans,
    COUNT(CASE WHEN l.status = 'active' THEN 1 END) as active_loans,
    COUNT(CASE WHEN l.status = 'returned' AND l.actual_return_date > l.expected_return_date THEN 1 END) as late_returns,
    MAX(l.loan_date) as last_loan_date
FROM students s
LEFT JOIN loans l ON s.student_id = l.student_id
GROUP BY s.student_id, s.student_number, s.first_name, s.last_name
ORDER BY total_loans DESC;

-- =====================================
-- 6. BUSINESS ANALYTICS
-- =====================================

SELECT 'ANALYTICS SECTION' as section;

-- Most popular books (by loan count)
SELECT 
    b.title,
    b.author,
    COUNT(l.loan_id) as loan_count,
    MAX(l.loan_date) as last_loaned
FROM books b
JOIN loans l ON b.book_id = l.book_id
GROUP BY b.book_id, b.title, b.author
ORDER BY loan_count DESC
LIMIT 10;

-- Books that have never been loaned
SELECT 
    b.book_id,
    b.title,
    b.author,
    b.status,
    b.publication_year
FROM books b
LEFT JOIN loans l ON b.book_id = l.book_id
WHERE l.loan_id IS NULL
ORDER BY b.title;

-- Students with multiple active loans
SELECT 
    s.student_number,
    s.first_name || ' ' || s.last_name as student_name,
    COUNT(l.loan_id) as active_loans,
    STRING_AGG(b.title, ', ') as books_on_loan
FROM students s
JOIN loans l ON s.student_id = l.student_id
JOIN books b ON l.book_id = b.book_id
WHERE l.status = 'active'
GROUP BY s.student_id, s.student_number, s.first_name, s.last_name
HAVING COUNT(l.loan_id) > 1
ORDER BY active_loans DESC;

-- Average loan duration
SELECT 
    ROUND(AVG(actual_return_date - loan_date), 2) as avg_loan_days,
    COUNT(*) as returned_loans
FROM loans 
WHERE actual_return_date IS NOT NULL;

-- Books by section popularity
SELECT 
    s.section,
    s.main_topic,
    COUNT(l.loan_id) as total_loans
FROM shelves s
JOIN books b ON s.shelf_id = b.shelf_id
JOIN loans l ON b.book_id = l.book_id
GROUP BY s.section, s.main_topic
ORDER BY total_loans DESC;

-- =====================================
-- 7. DATA INTEGRITY CHECKS
-- =====================================

SELECT 'DATA INTEGRITY SECTION' as section;

-- Check for orphaned records
SELECT 'Orphaned Books (invalid shelf_id)' as check_type, COUNT(*) as count
FROM books b
LEFT JOIN shelves s ON b.shelf_id = s.shelf_id
WHERE b.shelf_id IS NOT NULL AND s.shelf_id IS NULL

UNION ALL

SELECT 'Orphaned Loans (invalid student_id)', COUNT(*)
FROM loans l
LEFT JOIN students s ON l.student_id = s.student_id
WHERE s.student_id IS NULL

UNION ALL

SELECT 'Orphaned Loans (invalid book_id)', COUNT(*)
FROM loans l
LEFT JOIN books b ON l.book_id = b.book_id
WHERE b.book_id IS NULL;

-- Check email format in students
SELECT 'Invalid email formats' as check_type, COUNT(*) as count
FROM students 
WHERE email NOT LIKE '%@%.%';

-- Check for duplicate ISBNs
SELECT 
    isbn,
    COUNT(*) as duplicate_count
FROM books 
WHERE isbn IS NOT NULL
GROUP BY isbn
HAVING COUNT(*) > 1;

-- Check shelf capacity consistency
SELECT 
    s.location_code,
    s.current_book_count as recorded_count,
    COUNT(b.book_id) as actual_count,
    CASE 
        WHEN s.current_book_count = COUNT(b.book_id) THEN 'OK'
        ELSE 'MISMATCH'
    END as status
FROM shelves s
LEFT JOIN books b ON s.shelf_id = b.shelf_id AND b.book_type = 'physical'
GROUP BY s.shelf_id, s.location_code, s.current_book_count
ORDER BY s.location_code;

-- =====================================
-- 8. SAMPLE OPERATIONS (TESTING CRUD)
-- =====================================

SELECT 'SAMPLE OPERATIONS SECTION' as section;

-- Create a test student (uncomment to use)
/*
INSERT INTO students (student_number, first_name, last_name, email, program, enrollment_year)
VALUES ('2024999', 'Test', 'Student', 'test.student@uniandes.edu.co', 'Testing Program', 2024);
*/

-- Create a test book (uncomment to use)
/*
INSERT INTO books (isbn, title, author, publisher, publication_year, language, pages, shelf_id)
VALUES ('9999999999999', 'Test Book', 'Test Author', 'Test Publisher', 2024, 'English', 100, 1);
*/

-- Create a test loan (uncomment to use - update IDs as needed)
/*
INSERT INTO loans (book_id, student_id, loan_date, expected_return_date, status)
VALUES (1, 1, CURRENT_DATE, CURRENT_DATE + INTERVAL '14 days', 'active');
*/

-- Return a book (uncomment to use - update loan_id as needed)
/*
UPDATE loans 
SET status = 'returned', actual_return_date = CURRENT_DATE
WHERE loan_id = 1 AND status = 'active';
*/

-- Search operations
SELECT 'Search Examples:' as info;

-- Search books by keyword
SELECT title, author FROM books 
WHERE title ILIKE '%algorithm%' OR author ILIKE '%algorithm%';

-- Search students by program
SELECT student_number, first_name, last_name, program 
FROM students 
WHERE program ILIKE '%sistemas%';

-- =====================================
-- 9. REPORTING QUERIES
-- =====================================

SELECT 'REPORTING SECTION' as section;

-- Monthly loan report
SELECT 
    TO_CHAR(loan_date, 'YYYY-MM') as month,
    COUNT(*) as total_loans,
    COUNT(CASE WHEN status = 'returned' THEN 1 END) as returned,
    COUNT(CASE WHEN status = 'active' THEN 1 END) as active,
    COUNT(CASE WHEN status = 'overdue' THEN 1 END) as overdue
FROM loans
GROUP BY TO_CHAR(loan_date, 'YYYY-MM')
ORDER BY month DESC;

-- Library utilization summary
SELECT 
    'Total Students' as metric, COUNT(*)::text as value FROM students
UNION ALL
SELECT 'Active Students', COUNT(*)::text FROM students WHERE status = 'active'
UNION ALL
SELECT 'Total Books', COUNT(*)::text FROM books
UNION ALL
SELECT 'Available Books', COUNT(*)::text FROM books WHERE status = 'available'
UNION ALL
SELECT 'Books on Loan', COUNT(*)::text FROM books WHERE status = 'loaned'
UNION ALL
SELECT 'Total Shelves', COUNT(*)::text FROM shelves
UNION ALL
SELECT 'Active Loans', COUNT(*)::text FROM loans WHERE status = 'active'
UNION ALL
SELECT 'Overdue Loans', COUNT(*)::text FROM loans WHERE status = 'overdue';

-- =====================================
-- END OF TESTING QUERIES
-- =====================================

SELECT 'Testing queries completed!' as final_message;