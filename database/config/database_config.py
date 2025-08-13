"""
Database configuration management for Library Management System
Supports PostgreSQL, MySQL, and SQLite databases
"""

import os
from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum

class DatabaseType(Enum):
    POSTGRESQL = "postgresql"

@dataclass
class DatabaseConfig:
    """Database configuration class"""
    db_type: DatabaseType
    host: Optional[str] = None
    port: Optional[int] = None
    database: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    sqlite_path: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> 'DatabaseConfig':
        """Create database config from environment variables"""
        return cls(
            db_type=DatabaseType.POSTGRESQL,
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', '5432')),
            database=os.getenv('DB_NAME', 'library_management'),
            username=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', '')
        )
    
    def get_connection_string(self) -> str:
        """Generate database connection string"""
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"

# Default configurations for different environments
DEFAULT_CONFIGS = {
    'development': DatabaseConfig(
        db_type=DatabaseType.POSTGRESQL,
        host='localhost',
        port=5432,
        database='library_management_dev',
        username='postgres',
        password=''
    ),
    'testing': DatabaseConfig(
        db_type=DatabaseType.POSTGRESQL,
        host='localhost',
        port=5432,
        database='library_management_test',
        username='postgres',
        password=''
    ),
    'production': DatabaseConfig(
        db_type=DatabaseType.POSTGRESQL,
        host='localhost',
        port=5432,
        database='library_management_prod',
        username='library_user',
        password=''  # Should be set via environment variable
    )
}

def get_config(environment: str = None) -> DatabaseConfig:
    """Get database configuration for specified environment"""
    if environment and environment in DEFAULT_CONFIGS:
        return DEFAULT_CONFIGS[environment]
    return DatabaseConfig.from_env()