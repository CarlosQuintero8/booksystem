# Requirements Document

## Introduction

This document outlines the requirements for designing and implementing a database model for a library management system developed by 5IG Solutions for the Universidad de los Andes. The system will manage books, students, loans, and shelf organization to support comprehensive library operations including inventory tracking, loan management, and organizational structure.

## Requirements

### Requirement 1

**User Story:** As a librarian, I want to view a complete inventory of all books in the library, so that I can manage the collection effectively and know what resources are available.

#### Acceptance Criteria

1. WHEN a librarian requests the book inventory THEN the system SHALL display all books with their current status (available or loaned)
2. WHEN displaying book information THEN the system SHALL include book title, author, ISBN, publication details, and current location
3. WHEN a book is currently loaned THEN the system SHALL indicate the loan status and expected return date
4. WHEN a book is available THEN the system SHALL show its shelf location and availability status

### Requirement 2

**User Story:** As a librarian, I want to track which student has borrowed which book, so that I can manage loans and contact students when necessary.

#### Acceptance Criteria

1. WHEN a book is loaned to a student THEN the system SHALL record the student's identification and contact information
2. WHEN querying loan records THEN the system SHALL display the complete borrowing history for any student
3. WHEN a student has active loans THEN the system SHALL show all currently borrowed books with their details
4. WHEN searching by book THEN the system SHALL show the current borrower if the book is loaned

### Requirement 3

**User Story:** As a librarian, I want to manage comprehensive loan information including dates and return tracking, so that I can enforce library policies and track overdue items.

#### Acceptance Criteria

1. WHEN a book is loaned THEN the system SHALL record the loan date automatically
2. WHEN creating a loan THEN the system SHALL calculate and store the estimated return date based on library policies
3. WHEN a book is returned THEN the system SHALL record the actual return date
4. WHEN a loan is overdue THEN the system SHALL identify loans where the actual return date is null and the estimated return date has passed
5. WHEN generating reports THEN the system SHALL calculate loan duration and identify patterns in borrowing behavior

### Requirement 4

**User Story:** As a librarian, I want to organize books into shelves with detailed characteristics, so that I can efficiently manage the physical library space and help patrons locate materials.

#### Acceptance Criteria

1. WHEN defining a shelf THEN the system SHALL store the location identifier (Section A, B, C, etc.)
2. WHEN categorizing shelves THEN the system SHALL assign a main topic (Economics, Science, Politics, etc.)
3. WHEN creating shelf records THEN the system SHALL document the material the shelf is made of
4. WHEN managing shelf capacity THEN the system SHALL track the total number of books each shelf can hold
5. WHEN placing books THEN the system SHALL ensure shelf capacity limits are not exceeded
6. WHEN searching for books THEN the system SHALL provide shelf location information to help with physical retrieval

### Requirement 5

**User Story:** As a system administrator, I want the database design to support basic scalability features, so that the system can handle library operations effectively.

#### Acceptance Criteria

1. WHEN introducing digital books THEN the system SHALL support both physical and digital book types with appropriate attributes
2. WHEN implementing loan policies THEN the system SHALL support configurable loan periods and rules
3. WHEN scaling operations THEN the system SHALL maintain performance with large datasets through proper indexing and relationships
4. WHEN managing capacity THEN the system SHALL automatically enforce shelf capacity limits
5. WHEN tracking loans THEN the system SHALL automatically update book and loan statuses

### Requirement 6

**User Story:** As a database administrator, I want a well-documented PostgreSQL database with clear implementation guidelines, so that the system can be properly implemented and maintained.

#### Acceptance Criteria

1. WHEN documenting the ER model THEN the system SHALL identify all key entities (Book, Student, Loan, Shelf) with their attributes
2. WHEN defining relationships THEN the system SHALL specify cardinality and participation constraints
3. WHEN providing implementation guidance THEN the system SHALL include SQL scripts for PostgreSQL schema creation
4. WHEN implementing the database THEN the system SHALL use PostgreSQL with proper triggers and constraints
5. WHEN maintaining the system THEN the system SHALL include proper primary keys, foreign keys, and constraints for data integrity