#!/usr/bin/env python3
"""
Complete database setup script for Library Management System
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database.config.database_config import get_config
from database.connection.database_connection import DatabaseConnection
from database.migrations.migration_manager import MigrationManager


def main():
    """Complete database setup"""
    print("Setting up Library Management System Database...")
    
    try:
        # Get configuration
        config = get_config()
        print(f"Using PostgreSQL database: {config.database}")
        
        # Create connection
        connection = DatabaseConnection(config)
        connection.connect()
        print("Connected to database")
        
        # Initialize migration manager
        migration_manager = MigrationManager(connection)
        
        # Run all migrations
        print("Running migrations...")
        success = migration_manager.migrate_up()
        
        if success:
            print("✅ Database setup completed successfully!")
            
            # Show migration status
            status = migration_manager.get_migration_status()
            print(f"Applied migrations: {status['applied_count']}")
            print(f"Pending migrations: {status['pending_count']}")
            
        else:
            print("❌ Database setup failed")
            return 1
            
    except Exception as e:
        print(f"❌ Error during setup: {e}")
        return 1
    finally:
        if 'connection' in locals():
            connection.disconnect()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())