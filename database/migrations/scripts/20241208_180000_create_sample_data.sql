-- Description: Create sample data for testing
-- Version: 20241208_180000
-- Created: 2024-12-08T18:00:00

-- UP
-- Insert sample data for testing

-- Sample shelves
INSERT INTO shelves (location_code, section, main_topic, material, total_capacity) VALUES
('A1', 'Section A', 'Computer Science', 'Wood', 50),
('A2', 'Section A', 'Mathematics', 'Wood', 45),
('B1', 'Section B', 'Physics', 'Metal', 40),
('B2', 'Section B', 'Chemistry', 'Metal', 35),
('C1', 'Section C', 'Literature', 'Wood', 60);

-- Sample students
INSERT INTO students (student_number, first_name, last_name, email, program, enrollment_year) VALUES
('2024001', 'Juan', 'Pérez', 'juan.perez@uniandes.edu.co', 'Ingeniería de Sistemas', 2024),
('2024002', 'María', 'González', 'maria.gonzalez@uniandes.edu.co', 'Matemáticas', 2024),
('2023001', 'Carlos', 'Rodríguez', 'carlos.rodriguez@uniandes.edu.co', 'Física', 2023),
('2023002', 'Ana', 'López', 'ana.lopez@uniandes.edu.co', 'Química', 2023),
('2022001', 'Luis', 'Martínez', 'luis.martinez@uniandes.edu.co', 'Literatura', 2022);

-- Sample books
INSERT INTO books (isbn, title, author, publisher, publication_year, language, pages, shelf_id) VALUES
('9780134685991', 'Effective Java', 'Joshua Bloch', 'Addison-Wesley', 2018, 'English', 412, 1),
('9780135166307', 'Clean Code', 'Robert C. Martin', 'Prentice Hall', 2008, 'English', 464, 1),
('9780321356680', 'Effective C++', 'Scott Meyers', 'Addison-Wesley', 2005, 'English', 320, 1),
('9780134494166', 'The Clean Coder', 'Robert C. Martin', 'Prentice Hall', 2011, 'English', 256, 1),
('9780201633610', 'Design Patterns', 'Gang of Four', 'Addison-Wesley', 1994, 'English', 395, 1),

('9780471317715', 'Introduction to Algorithms', 'Cormen, Leiserson, Rivest, Stein', 'MIT Press', 2009, 'English', 1312, 2),
('9780486612720', 'Calculus', 'Michael Spivak', 'Publish or Perish', 1994, 'English', 670, 2),
('9780134689517', 'Discrete Mathematics', 'Kenneth Rosen', 'McGraw-Hill', 2018, 'English', 1072, 2),

('9780134777597', 'University Physics', 'Young and Freedman', 'Pearson', 2019, 'English', 1600, 3),
('9780471804574', 'Fundamentals of Physics', 'Halliday, Resnick, Walker', 'Wiley', 2013, 'English', 1328, 3),

('9780134293936', 'Chemistry: The Central Science', 'Brown, LeMay, Bursten', 'Pearson', 2017, 'English', 1280, 4),
('9780321910295', 'General Chemistry', 'Petrucci, Herring, Madura', 'Pearson', 2016, 'English', 1456, 4),

('9780486280615', 'Don Quixote', 'Miguel de Cervantes', 'Dover Publications', 2005, 'Spanish', 1072, 5),
('9780486415871', 'Cien Años de Soledad', 'Gabriel García Márquez', 'Editorial Sudamericana', 1967, 'Spanish', 432, 5);

-- Sample loans (some active, some returned)
INSERT INTO loans (book_id, student_id, loan_date, estimated_return_date, actual_return_date, loan_status) VALUES
(1, 1, '2024-11-01', '2024-11-15', '2024-11-14', 'returned'),
(2, 1, '2024-11-20', '2024-12-04', NULL, 'active'),
(3, 2, '2024-11-15', '2024-11-29', '2024-12-01', 'returned'),
(4, 3, '2024-12-01', '2024-12-15', NULL, 'active'),
(5, 4, '2024-11-10', '2024-11-24', NULL, 'overdue');

-- DOWN
-- Remove sample data
DELETE FROM loans;
DELETE FROM books;
DELETE FROM students;
DELETE FROM shelves;