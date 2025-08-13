#!/usr/bin/env python3
"""
Database setup utility for Library Management System
Handles database initialization and migration setup
"""

import os
import sys
import logging
import argparse
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database.config.database_config import DatabaseConfig, DatabaseType, get_config
from database.connection.database_connection import DatabaseConnection
from database.migrations.migration_manager import MigrationManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_database(config: DatabaseConfig, force: bool = False):
    """Initialize database with appropriate setup script"""
    
    logger.info(f"Setting up {config.db_type.value} database...")
    
    # Create database directory for SQLite
    if config.db_type == DatabaseType.SQLITE and config.sqlite_path:
        db_dir = os.path.dirname(config.sqlite_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
    
    # Get the appropriate initialization script
    script_path = None
    if config.db_type == DatabaseType.POSTGRESQL:
        script_path = "database/scripts/init_postgresql.sql"
    elif config.db_type == DatabaseType.MYSQL:
        script_path = "database/scripts/init_mysql.sql"
    elif config.db_type == DatabaseType.SQLITE:
        script_path = "database/scripts/init_sqlite.sql"
    
    if not script_path or not os.path.exists(script_path):
        logger.error(f"Initialization script not found: {script_path}")
        return False
    
    try:
        # Create database connection
        connection = DatabaseConnection(config)
        connection.connect()
        
        # Check if database is already initialized
        if not force and connection.table_exists('system_config'):
            logger.warning("Database appears to be already initialized. Use --force to reinitialize.")
            return False
        
        # Read and execute initialization script
        with open(script_path, 'r', encoding='utf-8') as f:
            init_script = f.read()
        
        logger.info("Executing initialization script...")
        connection.execute_script(init_script)
        
        logger.info("Database initialization completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False
    finally:
        if 'connection' in locals():
            connection.disconnect()

def setup_migrations(config: DatabaseConfig):
    """Setup migration system"""
    
    logger.info("Setting up migration system...")
    
    try:
        connection = DatabaseConnection(config)
        connection.connect()
        
        migration_manager = MigrationManager(connection)
        
        # Create initial migration for core tables
        migration_path = migration_manager.create_migration(
            "create_core_tables",
            "Create core tables for library management system"
        )
        
        logger.info(f"Created initial migration: {migration_path}")
        logger.info("Migration system setup completed")
        
        return True
        
    except Exception as e:
        logger.error(f"Migration setup failed: {e}")
        return False
    finally:
        if 'connection' in locals():
            connection.disconnect()

def verify_setup(config: DatabaseConfig):
    """Verify database setup"""
    
    logger.info("Verifying database setup...")
    
    try:
        connection = DatabaseConnection(config)
        connection.connect()
        
        # Check for required tables/views
        required_items = ['audit_log']
        
        if config.db_type == DatabaseType.SQLITE:
            required_items.extend(['system_config', 'system_log'])
        
        missing_items = []
        for item in required_items:
            if not connection.table_exists(item):
                missing_items.append(item)
        
        if missing_items:
            logger.error(f"Missing required database items: {missing_items}")
            return False
        
        # Test basic operations
        test_query = "SELECT 1 as test"
        result = connection.execute_query(test_query)
        
        if not result or result[0]['test'] != 1:
            logger.error("Basic query test failed")
            return False
        
        logger.info("Database setup verification passed")
        return True
        
    except Exception as e:
        logger.error(f"Database verification failed: {e}")
        return False
    finally:
        if 'connection' in locals():
            connection.disconnect()

def main():
    """Main setup function"""
    
    parser = argparse.ArgumentParser(description='Library Management System Database Setup')
    parser.add_argument('--db-type', choices=['postgresql', 'mysql', 'sqlite'], 
                       help='Database type (overrides environment)')
    parser.add_argument('--force', action='store_true', 
                       help='Force reinitialize even if database exists')
    parser.add_argument('--skip-migrations', action='store_true',
                       help='Skip migration system setup')
    parser.add_argument('--verify-only', action='store_true',
                       help='Only verify existing setup')
    parser.add_argument('--environment', choices=['development', 'testing', 'production'],
                       help='Use predefined environment configuration')
    
    args = parser.parse_args()
    
    # Get database configuration
    if args.environment:
        from database.config.database_config import DEFAULT_CONFIGS
        config = DEFAULT_CONFIGS[args.environment]
    else:
        config = get_config()
    
    # Override database type if specified
    if args.db_type:
        config.db_type = DatabaseType(args.db_type)
    
    logger.info(f"Using {config.db_type.value} database")
    
    # Verify only mode
    if args.verify_only:
        success = verify_setup(config)
        sys.exit(0 if success else 1)
    
    # Initialize database
    if not setup_database(config, args.force):
        logger.error("Database setup failed")
        sys.exit(1)
    
    # Setup migrations
    if not args.skip_migrations:
        if not setup_migrations(config):
            logger.error("Migration setup failed")
            sys.exit(1)
    
    # Verify setup
    if not verify_setup(config):
        logger.error("Setup verification failed")
        sys.exit(1)
    
    logger.info("Database setup completed successfully!")
    
    # Print next steps
    print("\nNext steps:")
    print("1. Review and customize the generated migration file")
    print("2. Run migrations: python -m database.migrations.migration_manager")
    print("3. Create your application tables using the migration system")

if __name__ == "__main__":
    main()