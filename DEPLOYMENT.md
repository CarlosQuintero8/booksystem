# Deployment Guide

## Prerequisites

- PostgreSQL 12+ installed and running
- Python 3.8+ with pip
- Database user with CREATE privileges

## Installation Steps

### 1. Setup Environment

```bash
# Clone project
git clone <repository-url>
cd library-management-database

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
```

### 2. Configure Database

Edit `.env` file:
```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=library_management
DB_USER=your_db_user
DB_PASSWORD=your_password
```

### 3. Create Database

```sql
-- Connect to PostgreSQL as superuser
CREATE DATABASE library_management;
CREATE USER library_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE library_management TO library_user;
```

### 4. Run Setup

```bash
# Complete database setup
python database/setup_complete.py
```

## Maintenance

### Daily Tasks
- Run overdue loan updates: `SELECT batch_update_overdue_loans();`
- Check system logs for errors

### Weekly Tasks
- Validate shelf capacity consistency: `SELECT * FROM validate_shelf_capacity_consistency();`
- Review audit logs for unusual activity

### Monthly Tasks
- Backup database
- Update statistics
- Review performance metrics

## Backup & Recovery

### Backup
```bash
pg_dump -h localhost -U library_user library_management > backup_$(date +%Y%m%d).sql
```

### Restore
```bash
psql -h localhost -U library_user library_management < backup_file.sql
```

## Troubleshooting

### Common Issues

1. **Connection Failed**
   - Check PostgreSQL service is running
   - Verify credentials in .env
   - Test network connectivity

2. **Migration Errors**
   - Check database permissions
   - Review migration logs
   - Ensure no conflicting data

3. **Performance Issues**
   - Run ANALYZE on tables
   - Check for missing indexes
   - Review slow query logs

### Performance Tuning

```sql
-- Update table statistics
ANALYZE students;
ANALYZE books;
ANALYZE loans;
ANALYZE shelves;

-- Check index usage
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;
```

## Monitoring

### Key Metrics
- Active loans count
- Overdue loans percentage
- Shelf utilization rates
- Database connection count

### Health Checks
```sql
-- System health
SELECT 
    COUNT(*) as total_students,
    (SELECT COUNT(*) FROM books WHERE status = 'available') as available_books,
    (SELECT COUNT(*) FROM loans WHERE loan_status = 'active') as active_loans,
    (SELECT COUNT(*) FROM loans WHERE loan_status = 'overdue') as overdue_loans;
```