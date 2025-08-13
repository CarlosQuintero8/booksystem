# Library Management System Database

Simple database for a library management system developed for Universidad de los Andes.

## Features

- **PostgreSQL Database**: Complete schema for library operations
- **Core Tables**: Students, Books, Shelves, and Loans
- **Business Logic**: Automatic shelf capacity and loan status management
- **Migration System**: Version-controlled schema changes

## Quick Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Database

```bash
# Copy and edit environment file
cp .env.example .env

# Edit .env with your PostgreSQL settings:
DB_HOST=localhost
DB_PORT=5432
DB_NAME=library_management
DB_USER=postgres
DB_PASSWORD=your_password
```

### 3. Setup Database

```bash
# Complete setup with sample data
python database/setup_complete.py
```

## Database Schema

### Tables

- **students**: Student information and enrollment details
- **shelves**: Physical shelf organization with capacity tracking
- **books**: Book inventory with shelf assignments
- **loans**: Loan transactions with date validation

### Key Features

- Automatic shelf capacity enforcement
- Loan status management with overdue detection
- Referential integrity with foreign keys
- Audit trail for all changes

## Usage Examples

### Using Repositories

```python
from database.config.database_config import get_config
from database.connection.database_connection import DatabaseConnection
from database.repositories.student_repository import StudentRepository

# Setup connection
config = get_config()
conn = DatabaseConnection(config)
conn.connect()

# Use repository
student_repo = StudentRepository(conn)

# Create student
student_id = student_repo.create({
    'student_number': '2024001',
    'first_name': 'Juan',
    'last_name': 'Pérez',
    'email': 'juan.perez@uniandes.edu.co',
    'program': 'Ingeniería de Sistemas'
})

# Get student
student = student_repo.get_by_id(student_id)
```

### Basic Queries

```python
# Get all available books
books = conn.execute_query("SELECT * FROM available_books")

# Get overdue loans
overdue = conn.execute_query("SELECT * FROM overdue_loans")

# Get shelf utilization
utilization = conn.execute_query("SELECT * FROM shelf_utilization")
```

## Project Structure

```
database/
├── config/           # Database configuration
├── connection/       # Connection management
├── migrations/       # Schema migrations
├── repositories/     # Data access layer
├── tables/          # Table managers
└── scripts/         # Setup scripts
```

## Running Tests

```bash
pytest tests/
```

## Sample Data

The setup includes sample data:

- 5 shelves in different sections (A1, A2, B1, B2, C1)
- 5 students from different programs
- 14 books across various topics (Computer Science, Math, Physics, Chemistry, Literature)
- Sample loan transactions (active, returned, and overdue loans)

## License

Developed for Universidad de los Andes.
