"""
Database migration management system for Library Management System
Handles schema versioning and migration execution
"""

import os
import logging
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass
from database.connection.database_connection import DatabaseConnection

logger = logging.getLogger(__name__)

@dataclass
class Migration:
    """Migration metadata"""
    version: str
    name: str
    description: str
    up_script: str
    down_script: str
    created_at: datetime

class MigrationManager:
    """Manages database schema migrations"""
    
    def __init__(self, connection: DatabaseConnection, migrations_dir: str = "database/migrations/scripts"):
        self.connection = connection
        self.migrations_dir = migrations_dir
        self._ensure_migrations_table()
    
    def _ensure_migrations_table(self):
        """Create migrations tracking table if it doesn't exist"""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version VARCHAR(50) PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            description TEXT,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            checksum VARCHAR(64)
        )
        """
        
        try:
            self.connection.execute_command(create_table_sql)
            logger.info("Migrations table ensured")
        except Exception as e:
            logger.error(f"Failed to create migrations table: {e}")
            raise
    
    def get_applied_migrations(self) -> List[str]:
        """Get list of applied migration versions"""
        query = "SELECT version FROM schema_migrations ORDER BY version"
        results = self.connection.execute_query(query)
        return [row['version'] for row in results]
    
    def get_pending_migrations(self) -> List[Migration]:
        """Get list of pending migrations"""
        applied = set(self.get_applied_migrations())
        all_migrations = self._load_migrations()
        
        return [migration for migration in all_migrations if migration.version not in applied]
    
    def _load_migrations(self) -> List[Migration]:
        """Load all migration files from migrations directory"""
        migrations = []
        
        if not os.path.exists(self.migrations_dir):
            os.makedirs(self.migrations_dir)
            return migrations
        
        for filename in sorted(os.listdir(self.migrations_dir)):
            if filename.endswith('.sql'):
                migration = self._parse_migration_file(filename)
                if migration:
                    migrations.append(migration)
        
        return migrations
    
    def _parse_migration_file(self, filename: str) -> Optional[Migration]:
        """Parse migration file and extract metadata"""
        filepath = os.path.join(self.migrations_dir, filename)
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract version from filename (format: YYYYMMDD_HHMMSS_name.sql)
            version = filename.split('_')[0] + '_' + filename.split('_')[1]
            name = '_'.join(filename.split('_')[2:]).replace('.sql', '')
            
            # Split content into UP and DOWN sections
            sections = content.split('-- DOWN')
            up_script = sections[0].replace('-- UP', '').strip()
            down_script = sections[1].strip() if len(sections) > 1 else ""
            
            # Extract description from comments
            description = ""
            for line in content.split('\n'):
                if line.startswith('-- Description:'):
                    description = line.replace('-- Description:', '').strip()
                    break
            
            return Migration(
                version=version,
                name=name,
                description=description,
                up_script=up_script,
                down_script=down_script,
                created_at=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Failed to parse migration file {filename}: {e}")
            return None
    
    def apply_migration(self, migration: Migration) -> bool:
        """Apply a single migration"""
        try:
            logger.info(f"Applying migration {migration.version}: {migration.name}")
            
            # Execute the UP script
            self.connection.execute_script(migration.up_script)
            
            # Record migration as applied
            insert_sql = """
            INSERT INTO schema_migrations (version, name, description, applied_at)
            VALUES (?, ?, ?, ?)
            """
            
            self.connection.execute_command(
                insert_sql,
                (migration.version, migration.name, migration.description, datetime.now())
            )
            
            logger.info(f"Successfully applied migration {migration.version}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply migration {migration.version}: {e}")
            return False
    
    def rollback_migration(self, version: str) -> bool:
        """Rollback a specific migration"""
        try:
            # Find the migration
            migration = None
            for m in self._load_migrations():
                if m.version == version:
                    migration = m
                    break
            
            if not migration:
                logger.error(f"Migration {version} not found")
                return False
            
            if not migration.down_script:
                logger.error(f"No rollback script for migration {version}")
                return False
            
            logger.info(f"Rolling back migration {version}: {migration.name}")
            
            # Execute the DOWN script
            self.connection.execute_script(migration.down_script)
            
            # Remove migration record
            delete_sql = "DELETE FROM schema_migrations WHERE version = ?"
            self.connection.execute_command(delete_sql, (version,))
            
            logger.info(f"Successfully rolled back migration {version}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to rollback migration {version}: {e}")
            return False
    
    def migrate_up(self, target_version: Optional[str] = None) -> bool:
        """Apply all pending migrations up to target version"""
        pending = self.get_pending_migrations()
        
        if target_version:
            pending = [m for m in pending if m.version <= target_version]
        
        if not pending:
            logger.info("No pending migrations to apply")
            return True
        
        logger.info(f"Applying {len(pending)} migrations")
        
        for migration in pending:
            if not self.apply_migration(migration):
                logger.error(f"Migration failed at {migration.version}")
                return False
        
        logger.info("All migrations applied successfully")
        return True
    
    def get_migration_status(self) -> Dict[str, any]:
        """Get current migration status"""
        applied = self.get_applied_migrations()
        pending = self.get_pending_migrations()
        
        return {
            'applied_count': len(applied),
            'pending_count': len(pending),
            'applied_versions': applied,
            'pending_versions': [m.version for m in pending],
            'current_version': applied[-1] if applied else None
        }
    
    def create_migration(self, name: str, description: str = "") -> str:
        """Create a new migration file template"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        version = timestamp
        filename = f"{timestamp}_{name}.sql"
        filepath = os.path.join(self.migrations_dir, filename)
        
        template = f"""-- Description: {description}
-- Version: {version}
-- Created: {datetime.now().isoformat()}

-- UP
-- Add your schema changes here


-- DOWN
-- Add rollback statements here

"""
        
        os.makedirs(self.migrations_dir, exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(template)
        
        logger.info(f"Created migration file: {filepath}")
        return filepath